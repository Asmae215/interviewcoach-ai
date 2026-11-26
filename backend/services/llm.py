import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

# Les incidents (réessai, passage au fournisseur de secours) sont journalisés ici
logger = logging.getLogger("interviewcoach.llm")

# Pannes passagères du serveur : on réessaie le même fournisseur après une courte attente.
# 429 (quota gratuit atteint) n'en fait pas partie : attendre ne sert à rien,
# on passe tout de suite à l'autre fournisseur (réponse plus rapide pour le candidat).
RETRY_CODES = {500, 502, 503}
MAX_ATTEMPTS = 3


class LLMError(Exception):
    """Erreur lors de l'appel au modèle."""


def _post_with_retry(url: str, headers: dict, body: dict) -> dict:
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=60)
        except requests.RequestException as error:  # réseau coupé, délai dépassé...
            raise LLMError(f"Service injoignable : {error}") from error
        if response.status_code == 200:
            return response.json()
        last_error = f"Erreur {response.status_code} : {response.text[:300]}"
        if response.status_code in RETRY_CODES and attempt < MAX_ATTEMPTS:
            wait = 2 ** attempt
            logger.warning("Erreur %s, nouvel essai dans %s s", response.status_code, wait)
            time.sleep(wait)
            continue
        break
    raise LLMError(last_error)


def _gemini(
    prompt: str, system: str | None, temperature: float, max_tokens: int, json_mode: bool
) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY manquante dans .env")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    data = _post_with_retry(
        url, {"x-goog-api-key": key, "Content-Type": "application/json"}, body
    )
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise LLMError(f"Réponse Gemini inattendue : {str(data)[:300]}")


def _groq(
    prompt: str, system: str | None, temperature: float, max_tokens: int, json_mode: bool
) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY manquante dans .env")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = _post_with_retry(
        "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        body,
    )
    try:
        text = data["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError):
        raise LLMError(f"Réponse Groq inattendue : {str(data)[:300]}")
    if not text.strip():
        raise LLMError("Groq a renvoyé une réponse vide")
    return text


PROVIDERS = {"gemini": _gemini, "groq": _groq}


def ask_llm(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    json_mode: bool = False,
) -> str:
    """Envoie un message au modèle et renvoie sa réponse en texte.

    Le fournisseur principal est choisi par LLM_PROVIDER dans .env
    (gemini ou groq) ; en cas d'échec, l'autre est essayé.
    json_mode=True demande au modèle de répondre uniquement en JSON.
    """
    primary = os.getenv("LLM_PROVIDER", "gemini").lower()
    if primary not in PROVIDERS:
        raise LLMError(f"LLM_PROVIDER inconnu : {primary} (gemini ou groq)")
    order = [primary] + [name for name in PROVIDERS if name != primary]

    errors = []
    for name in order:
        try:
            return PROVIDERS[name](prompt, system, temperature, max_tokens, json_mode).strip()
        except LLMError as error:
            logger.warning("%s indisponible : %s", name, str(error)[:120])
            errors.append(f"{name} : {error}")
    raise LLMError(" | ".join(errors))
