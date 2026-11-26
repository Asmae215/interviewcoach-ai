"""Analyse du CV par le LLM : texte brut -> JSON structuré validé par Pydantic (étape 5)."""

import re
from pathlib import Path

from pydantic import ValidationError

from backend.schemas import CVAnalysis
from backend.services.llm import ask_llm

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
MAX_RETRIES = 2  # réessais si le JSON est invalide (donc 3 essais au total)

LEVEL_LABELS = {
    "fr": {"etudiant": "étudiant", "junior": "junior", "confirme": "confirmé"},
    "en": {"etudiant": "student", "junior": "junior", "confirme": "experienced"},
}


# Messages d'erreur montrés au candidat
MESSAGES: dict[str, dict[str, str]] = {
    "consent_required": {
        "fr": "Ton accord est nécessaire : le CV est analysé par un service d'IA externe.",
        "en": "Your consent is required: the CV is analysed by an external AI service.",
    },
    "no_text": {
        "fr": "Ce CV n'a pas de texte à analyser. Dépose-le à nouveau.",
        "en": "This CV has no text to analyse. Please upload it again.",
    },
    "llm_unavailable": {
        "fr": "Le service d'IA est indisponible ou son quota gratuit est atteint. Réessaie dans quelques minutes.",
        "en": "The AI service is unavailable or its free quota is reached. Try again in a few minutes.",
    },
    "analysis_failed": {
        "fr": "L'IA n'a pas réussi à produire une analyse valide. Réessaie.",
        "en": "The AI could not produce a valid analysis. Please retry.",
    },
}

RETRY_NOTE = {
    "fr": "\n\nTa réponse précédente était invalide : {error}\nRenvoie uniquement l'objet JSON demandé.",
    "en": "\n\nYour previous answer was invalid: {error}\nReturn only the requested JSON object.",
}


class CVAnalysisError(Exception):
    """Le modèle n'a pas renvoyé de JSON valide après tous les essais."""


def load_prompt(language: str) -> str:
    return (PROMPTS_DIR / f"cv_analysis_{language}.txt").read_text(encoding="utf-8")


def build_user_message(cv_text: str, target_job: str, level: str, language: str) -> str:
    """Message envoyé au modèle : contexte du poste + CV entre balises."""
    # Empêche le CV de « fermer » la balise pour sortir de la zone de données
    safe_cv = re.sub(r"</?cv>", "", cv_text, flags=re.IGNORECASE)
    level_label = LEVEL_LABELS[language].get(level, level)
    if language == "en":
        header = f"Target job: {target_job}\nLevel: {level_label}"
    else:
        header = f"Poste visé : {target_job}\nNiveau : {level_label}"
    return f"{header}\n\n<cv>\n{safe_cv}\n</cv>"


def extract_json(raw: str) -> str:
    """Retire un éventuel bloc ```json et garde le texte entre la première { et la dernière }."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end < start:
        return raw
    return raw[start : end + 1]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def keep_real_skills(analysis: CVAnalysis, cv_text: str) -> CVAnalysis:
    """Garde-fou anti-invention : on retire les compétences absentes du texte du CV."""
    cv_normalized = _normalize(cv_text)
    skills = [s for s in analysis.skills if s.strip() and _normalize(s) in cv_normalized]
    return analysis.model_copy(update={"skills": skills})


def analyze_cv(cv_text: str, target_job: str, level: str, language: str) -> CVAnalysis:
    """Analyse le CV avec le LLM. Lève LLMError (service) ou CVAnalysisError (JSON)."""
    language = language if language in ("fr", "en") else "fr"
    system = load_prompt(language)
    message = build_user_message(cv_text, target_job, level, language)

    last_error = ""
    for _ in range(1 + MAX_RETRIES):
        prompt = message
        if last_error:
            # On rappelle au modèle pourquoi sa réponse précédente a été refusée
            prompt += RETRY_NOTE[language].format(error=last_error[:300])
        raw = ask_llm(prompt, system=system, temperature=0.2, json_mode=True)
        try:
            analysis = CVAnalysis.model_validate_json(extract_json(raw))
        except ValidationError as error:
            last_error = str(error)
            continue
        return keep_real_skills(analysis, cv_text)

    raise CVAnalysisError(f"JSON invalide après {1 + MAX_RETRIES} essais : {last_error[:300]}")
