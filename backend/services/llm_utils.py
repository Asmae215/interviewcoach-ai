"""Outils communs autour de ask_llm : réponses JSON validées par Pydantic, données balisées."""

import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend.services.llm import ask_llm

MAX_RETRIES = 2  # réessais si le JSON est invalide (donc 3 essais au total)

RETRY_NOTE = {
    "fr": "\n\nTa réponse précédente était invalide : {error}\nRenvoie uniquement l'objet JSON demandé.",
    "en": "\n\nYour previous answer was invalid: {error}\nReturn only the requested JSON object.",
}

# Balises qui entourent les données (CV, réponses...) dans les prompts
DATA_TAGS = r"cv|cv_analysis|historique|history|reponse|answer|question_source"

# Messages montrés au candidat quand le LLM échoue (réutilisés par les routes)
LLM_ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "llm_unavailable": {
        "fr": "Le service d'IA est indisponible ou son quota gratuit est atteint. Réessaie dans quelques minutes.",
        "en": "The AI service is unavailable or its free quota is reached. Try again in a few minutes.",
    },
    "generation_failed": {
        "fr": "L'IA n'a pas réussi à produire une réponse valide. Réessaie.",
        "en": "The AI could not produce a valid answer. Please retry.",
    },
}

Model = TypeVar("Model", bound=BaseModel)


class LLMJSONError(Exception):
    """Le modèle n'a pas renvoyé de JSON valide après tous les essais."""


def strip_data_tags(text: str) -> str:
    """Retire nos balises d'un texte fourni par le candidat : il ne peut pas sortir de sa zone de données."""
    return re.sub(rf"</?\s*(?:{DATA_TAGS})\s*>", "", text, flags=re.IGNORECASE)


def extract_json(raw: str) -> str:
    """Retire un éventuel bloc ```json et garde le texte entre la première { et la dernière }."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end < start:
        return raw
    return raw[start : end + 1]


def ask_json(
    prompt: str,
    system: str,
    model: type[Model],
    language: str = "fr",
    temperature: float = 0.2,
) -> Model:
    """Appelle le LLM en mode JSON et valide la réponse ; réessaie au plus MAX_RETRIES fois.

    Lève LLMError (service indisponible) ou LLMJSONError (JSON toujours invalide).
    """
    last_error = ""
    for _ in range(1 + MAX_RETRIES):
        full_prompt = prompt
        if last_error:
            # On rappelle au modèle pourquoi sa réponse précédente a été refusée
            full_prompt += RETRY_NOTE.get(language, RETRY_NOTE["fr"]).format(error=last_error[:300])
        raw = ask_llm(full_prompt, system=system, temperature=temperature, json_mode=True)
        try:
            return model.model_validate_json(extract_json(raw))
        except ValidationError as error:
            last_error = str(error)
    raise LLMJSONError(f"JSON invalide après {1 + MAX_RETRIES} essais : {last_error[:300]}")
