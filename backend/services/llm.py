import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

RETRY_CODES = {429, 500, 503}
MAX_ATTEMPTS = 4


class LLMError(Exception):
    """Erreur lors de l'appel au modèle."""


def ask_llm(prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
    """Envoie un message au modèle et renvoie sa réponse en texte."""
    if not API_KEY:
        raise LLMError("GEMINI_API_KEY introuvable dans le fichier .env")

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.post(
            URL,
            headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
        if response.status_code == 200:
            break
        if response.status_code in RETRY_CODES and attempt < MAX_ATTEMPTS:
            time.sleep(2 ** attempt)
            continue
        raise LLMError(f"Erreur {response.status_code} : {response.text[:300]}")

    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise LLMError(f"Réponse inattendue : {str(data)[:300]}")
