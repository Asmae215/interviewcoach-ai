"""Analyse du CV par le LLM : texte brut -> JSON structuré validé par Pydantic (étape 5)."""

import re
from pathlib import Path

from backend.schemas import CVAnalysis
from backend.services.llm_utils import LLM_ERROR_MESSAGES, LLMJSONError, ask_json, strip_data_tags

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

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
    "analysis_failed": {
        "fr": "L'IA n'a pas réussi à produire une analyse valide. Réessaie.",
        "en": "The AI could not produce a valid analysis. Please retry.",
    },
    **LLM_ERROR_MESSAGES,
}

# Nom gardé pour la route du CV : même erreur que celle du module commun
CVAnalysisError = LLMJSONError


def load_prompt(language: str) -> str:
    return (PROMPTS_DIR / f"cv_analysis_{language}.txt").read_text(encoding="utf-8")


def build_user_message(cv_text: str, target_job: str, level: str, language: str) -> str:
    """Message envoyé au modèle : contexte du poste + CV entre balises."""
    safe_cv = strip_data_tags(cv_text)  # le CV ne peut pas « fermer » la balise <cv>
    level_label = LEVEL_LABELS[language].get(level, level)
    if language == "en":
        header = f"Target job: {target_job}\nLevel: {level_label}"
    else:
        header = f"Poste visé : {target_job}\nNiveau : {level_label}"
    return f"{header}\n\n<cv>\n{safe_cv}\n</cv>"


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
    analysis = ask_json(
        build_user_message(cv_text, target_job, level, language),
        system=load_prompt(language),
        model=CVAnalysis,
        language=language,
        temperature=0.2,
    )
    return keep_real_skills(analysis, cv_text)
