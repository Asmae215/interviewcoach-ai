"""Tests du client LLM unique (services/llm.py), sans réseau : requests.post est simulé."""

from unittest import mock

import pytest

from backend.services import llm
from backend.services.llm import LLMError, ask_llm


def response(status: int, text: str = "Bonjour") -> mock.Mock:
    result = mock.Mock(status_code=status, text="erreur")
    result.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": text}]}}],  # format Gemini
        "choices": [{"message": {"content": text}}],  # format Groq
    }
    return result


@pytest.fixture(autouse=True)
def keys(monkeypatch: pytest.MonkeyPatch) -> mock.Mock:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "cle-test")
    monkeypatch.setenv("GROQ_API_KEY", "cle-test")
    sleep = mock.Mock()
    monkeypatch.setattr(llm.time, "sleep", sleep)  # aucune vraie attente pendant les tests
    return sleep


def urls(post: mock.Mock) -> list[str]:
    return ["groq" if "groq" in call.args[0] else "gemini" for call in post.call_args_list]


def test_answer_from_primary_provider() -> None:
    with mock.patch.object(llm.requests, "post", return_value=response(200, " Salut ")) as post:
        assert ask_llm("Bonjour") == "Salut"
    assert urls(post) == ["gemini"]


def test_quota_switches_to_fallback_without_waiting(keys: mock.Mock) -> None:
    """429 (quota) : on passe tout de suite à Groq, sans attendre ni réessayer Gemini."""
    with mock.patch.object(llm.requests, "post", side_effect=[response(429), response(200, "Groq")]) as post:
        assert ask_llm("Bonjour") == "Groq"
    assert urls(post) == ["gemini", "groq"]
    keys.assert_not_called()


def test_server_error_is_retried(keys: mock.Mock) -> None:
    with mock.patch.object(llm.requests, "post", side_effect=[response(503), response(200)]) as post:
        assert ask_llm("Bonjour") == "Bonjour"
    assert urls(post) == ["gemini", "gemini"]
    keys.assert_called_once_with(2)


def test_both_providers_down() -> None:
    with mock.patch.object(llm.requests, "post", return_value=response(429)):
        with pytest.raises(LLMError) as info:
            ask_llm("Bonjour")
    assert "gemini" in str(info.value) and "groq" in str(info.value)


def test_network_error_becomes_llm_error() -> None:
    error = llm.requests.ConnectionError("réseau coupé")
    with mock.patch.object(llm.requests, "post", side_effect=[error, response(200, "Groq")]):
        assert ask_llm("Bonjour") == "Groq"


def test_json_mode_is_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    with mock.patch.object(llm.requests, "post", return_value=response(200, "{}")) as post:
        ask_llm("Bonjour", json_mode=True)
    assert post.call_args.kwargs["json"]["generationConfig"]["responseMimeType"] == "application/json"

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    with mock.patch.object(llm.requests, "post", return_value=response(200, "{}")) as post:
        ask_llm("Bonjour", json_mode=True)
    assert post.call_args.kwargs["json"]["response_format"] == {"type": "json_object"}


def test_incidents_are_logged(caplog: pytest.LogCaptureFixture) -> None:
    with mock.patch.object(llm.requests, "post", side_effect=[response(429), response(200)]):
        with caplog.at_level("WARNING", logger="interviewcoach.llm"):
            ask_llm("Bonjour")
    assert "gemini indisponible" in caplog.text
