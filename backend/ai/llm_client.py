"""Client LLM du recruteur de Lina : passe désormais par services/llm.py (un seul point d'appel)."""

from backend.services.llm import LLMError, ask_llm

RECRUITER_SYSTEM = (
    "Tu es InterviewCoach AI, un recruteur professionnel polyvalent. "
    "Respecte les instructions du candidat et génère une seule question précise."
)


def generate_response(prompt: str) -> str:
    """Génère une réponse textuelle avec le fournisseur configuré dans .env."""
    return ask_llm(prompt, system=RECRUITER_SYSTEM, temperature=0.4)


if __name__ == "__main__":
    try:
        question = generate_response(
            "Pose une seule question technique à un développeur Python junior."
        )
        print("\n=== INTERVIEWCOACH AI ===")
        print("\nQuestion générée :")
        print(question)
    except LLMError as erreur:
        print(f"Erreur : {erreur}")
