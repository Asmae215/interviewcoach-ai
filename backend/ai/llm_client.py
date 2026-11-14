
"""Connexion au modèle LLM via Groq - InterviewCoach AI."""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def generate_response(prompt: str) -> str:
    """Génère une réponse textuelle avec Groq."""

    if not GROQ_API_KEY:
        raise ValueError(
            "Clé GROQ_API_KEY manquante dans le fichier .env"
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu es InterviewCoach AI, un recruteur "
                    "professionnel polyvalent. "
                    "Respecte les instructions du candidat "
                    "et génère une seule question précise."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.4,
        "max_completion_tokens": 2048
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            GROQ_URL,
            headers=headers,
            json=payload
        )

        response.raise_for_status()

    data = response.json()
    choice = data["choices"][0]

    content = choice["message"].get("content") or ""
    finish_reason = choice.get("finish_reason")

    if not content.strip():
        raise ValueError(
            "Le modèle n'a généré aucun texte visible. "
            f"finish_reason={finish_reason}"
        )

    return content.strip()


if __name__ == "__main__":

    try:
        question = generate_response(
            "Pose une seule question technique "
            "à un développeur Python junior."
        )

        print("\n=== INTERVIEWCOACH AI ===")
        print("\nQuestion générée :")
        print(question)

    except httpx.HTTPStatusError as erreur:
        print(
            f"Erreur API : HTTP {erreur.response.status_code}"
        )

    except (httpx.RequestError, ValueError, KeyError) as erreur:
        print(f"Erreur : {erreur}")
