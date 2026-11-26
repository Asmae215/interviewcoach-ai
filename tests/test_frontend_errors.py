"""Tests des messages d'erreur affichés dans l'interface (frontend/errors.py)."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "frontend"))
from errors import format_validation_errors  # noqa: E402


def register_errors(client: TestClient, **fields) -> list[dict]:
    """Vraies erreurs renvoyées par l'API pour une inscription invalide."""
    payload = {"username": "asmae", "password": "motdepasse123", "name": "A",
               "target_job": "Dev", "level": "junior", "language": "fr", **fields}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 422
    return response.json()["detail"]


def test_short_username_in_french(client: TestClient) -> None:
    errors = register_errors(client, username="1")
    assert format_validation_errors(errors, "fr") == "Identifiant : au moins 3 caractères"


def test_short_username_in_english(client: TestClient) -> None:
    errors = register_errors(client, username="1")
    assert format_validation_errors(errors, "en") == "Username : at least 3 characters"


def test_forbidden_characters(client: TestClient) -> None:
    errors = register_errors(client, username="mon nom")
    assert "seulement des lettres" in format_validation_errors(errors, "fr")


def test_several_errors_and_empty_field(client: TestClient) -> None:
    errors = register_errors(client, password="court", name="")
    message = format_validation_errors(errors, "fr")
    assert "Mot de passe : au moins 8 caractères" in message
    assert "Nom : champ obligatoire" in message


def test_unknown_error_type_falls_back() -> None:
    assert format_validation_errors([{"loc": ["body", "x"], "type": "bizarre"}], "fr") == "x : valeur non valide"
