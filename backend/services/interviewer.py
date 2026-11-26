"""Recruteur IA (étape 6) : une question à la fois, relances, 6 à 8 questions.

Réutilise la banque de questions de Lina (backend/ai/question_selector.py) pour les
entretiens techniques et mixtes ; les autres questions sont créées à partir du CV.
Le modèle n'a pas de mémoire : l'analyse du CV et tout l'historique sont envoyés à chaque appel.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

from backend.ai.question_selector import contains_term, normalize, select_questions
from backend.services.cv_analyzer import LEVEL_LABELS
from backend.services.llm_utils import ask_json, strip_data_tags

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

# Nombre total de questions du recruteur (relances comprises) selon la difficulté
TOTAL_QUESTIONS = {"debutant": 6, "intermediaire": 7, "avance": 8}

# Emplacements où l'on place une question de la banque (les autres sont créées à partir du CV).
# La question 1 (index 0) est toujours une question d'ouverture liée au CV.
BANK_SLOTS = {"technique": (2, 4, 6), "mixte": (3, 6)}

# Domaines de la banque de Lina, reconnus à partir du poste visé
DOMAIN_KEYWORDS = {
    "cybersecurite": ["cyber", "cybersecurite", "securite", "security", "soc", "pentest", "pentester"],
    "data": [
        "data", "donnees", "machine learning", "ml", "ia", "ai",
        "intelligence artificielle", "analyst", "analyste", "statisticien",
    ],
    "developpement": [
        "developpeur", "developer", "dev", "full-stack", "fullstack", "backend", "back-end",
        "frontend", "front-end", "web", "logiciel", "software", "devops", "programmeur",
    ],
}

TYPE_LABELS = {
    "fr": {
        "rh": "RH (motivation, parcours, projet professionnel, qualités)",
        "technique": "technique (connaissances et savoir-faire du métier)",
        "comportemental": "comportemental (situations vécues : contexte, action, résultat)",
        "mixte": "mixte (alterner RH, technique et comportemental)",
    },
    "en": {
        "rh": "HR (motivation, background, career goals, qualities)",
        "technique": "technical (job knowledge and skills)",
        "comportemental": "behavioural (real situations: context, action, result)",
        "mixte": "mixed (alternate HR, technical and behavioural)",
    },
}

DIFFICULTY_LABELS = {
    "fr": {"debutant": "débutant", "intermediaire": "intermédiaire", "avance": "avancé"},
    "en": {"debutant": "beginner", "intermediaire": "intermediate", "avance": "advanced"},
}

CLOSING_MESSAGE = {
    "fr": "Merci pour vos réponses, l'entretien est terminé. Votre avis détaillé et vos pistes d'amélioration vont être préparés.",
    "en": "Thank you for your answers, the interview is over. Your detailed feedback and improvement tips will now be prepared.",
}


class RecruiterTurn(BaseModel):
    """Réponse JSON attendue du recruteur à chaque tour."""

    action: Literal["followup", "next"]
    question: str

    @field_validator("question")
    @classmethod
    def single_question(cls, value: str) -> str:
        """Règle de Lina : une seule question, terminée par un point d'interrogation."""
        value = value.strip().strip('"').strip()
        if not 10 <= len(value) <= 450:
            raise ValueError("la question doit faire entre 10 et 450 caractères")
        if value.count("?") != 1 or not value.endswith("?"):
            raise ValueError("il faut exactement une question, terminée par '?'")
        return value


def detect_domain(target_job: str) -> str | None:
    """Trouve le domaine de la banque de questions correspondant au poste (ou None)."""
    job = normalize(target_job)
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(contains_term(job, keyword) for keyword in keywords):
            return domain
    return None


def build_state(
    interview_type: str, difficulty: str, target_job: str, level: str, analysis: dict
) -> dict:
    """Prépare l'entretien : nombre de questions et questions de la banque à utiliser."""
    total = TOTAL_QUESTIONS[difficulty]
    bank: list[dict | None] = [None] * total

    domain = detect_domain(target_job)
    slots = [slot for slot in BANK_SLOTS.get(interview_type, ()) if slot < total]
    if domain and slots:
        profile = " ".join(analysis.get("skills", [])) + " " + analysis.get("summary", "")
        try:
            picked = select_questions(
                domain=domain, difficulty=difficulty, number=len(slots),
                cv_text=profile, job_title=target_job,
            )
        except (ValueError, OSError):  # banque absente ou filtre vide : on crée tout à partir du CV
            picked = []
        for slot, question in zip(slots, picked):
            bank[slot] = {"id": question["id"], "question": question["question"]}

    return {
        "total": total,
        "asked": 0,            # questions déjà posées (relances comprises)
        "main_index": -1,      # numéro de la question principale en cours
        "followup_used": False,  # une seule relance par question principale
        "bank": bank,
        "target_job": target_job,
        "level": level,
        "cv_analysis": analysis,  # copie : l'entretien reste cohérent si le CV change ensuite
    }


def is_finished(state: dict) -> bool:
    return state["asked"] >= state["total"]


def load_prompt(language: str) -> str:
    return (PROMPTS_DIR / f"recruiter_{language}.txt").read_text(encoding="utf-8")


def format_history(messages: list[tuple[str, str]], language: str) -> str:
    """Historique complet : questions du recruteur et réponses du candidat (balisées)."""
    if language == "en":
        recruiter, candidate, tag = "Recruiter", "Candidate", "answer"
    else:
        recruiter, candidate, tag = "Recruteur", "Candidat", "reponse"
    lines = []
    for role, content in messages:
        safe = strip_data_tags(content)
        if role == "recruiter":
            lines.append(f"{recruiter} : {safe}")
        else:
            lines.append(f"{candidate} : <{tag}>{safe}</{tag}>")
    return "\n".join(lines)


def build_user_message(
    state: dict, messages: list[tuple[str, str]], interview_type: str, difficulty: str, language: str
) -> str:
    """Message envoyé au modèle à chaque tour : contexte, consigne du tour, CV, historique."""
    first = state["asked"] == 0
    followup_allowed = not first and not state["followup_used"]
    next_main = state["main_index"] + 1
    bank_item = state["bank"][next_main] if next_main < len(state["bank"]) else None
    number = state["asked"] + 1
    last = number == state["total"]
    analysis = strip_data_tags(json.dumps(state["cv_analysis"], ensure_ascii=False, indent=1))
    history = format_history(messages, language)
    level = LEVEL_LABELS[language].get(state["level"], state["level"])

    if language == "en":
        if first:
            task = (
                'This is the first question: action = "next". Ask a general opening question: '
                "invite the candidate to present their background or motivation for the target job, "
                "mentioning one element of the CV (degree or experience). No detailed technical question."
            )
        elif followup_allowed:
            task = 'Choose: "followup" if the last answer deserves to be explored further, otherwise "next".'
        else:
            task = 'A follow-up is not allowed now: action = "next".'
        if bank_item:
            source = f"If action = next, use this question from the bank:\n<question_source>{bank_item['question']}</question_source>"
        else:
            source = "If action = next, create a question that mentions a precise element of the CV analysis."
        return (
            f"Target job: {state['target_job']}\nCandidate level: {level}\n"
            f"Interview type: {TYPE_LABELS['en'][interview_type]}\n"
            f"Difficulty: {DIFFICULTY_LABELS['en'][difficulty]}\n"
            f"Question {number} of {state['total']}{' (last question)' if last else ''}\n\n"
            f"{task}\n{source}\n\n"
            f"<cv_analysis>\n{analysis}\n</cv_analysis>\n\n"
            f"<history>\n{history or 'No exchange yet.'}\n</history>"
        )

    if first:
        task = (
            'C\'est la première question : action = "next". Pose une question d\'ouverture générale : '
            "invite le candidat à présenter son parcours ou sa motivation pour le poste visé, "
            "en citant un élément du CV (formation ou expérience). Pas de question technique pointue."
        )
    elif followup_allowed:
        task = 'Choisis : "followup" si la dernière réponse mérite d\'être approfondie, sinon "next".'
    else:
        task = 'Relance interdite pour ce tour : action = "next".'
    if bank_item:
        source = f"Si action = next, utilise cette question de la banque :\n<question_source>{bank_item['question']}</question_source>"
    else:
        source = "Si action = next, crée une question qui cite un élément précis de l'analyse du CV."
    return (
        f"Poste visé : {state['target_job']}\nNiveau du candidat : {level}\n"
        f"Type d'entretien : {TYPE_LABELS['fr'][interview_type]}\n"
        f"Difficulté : {DIFFICULTY_LABELS['fr'][difficulty]}\n"
        f"Question {number} sur {state['total']}{' (dernière question)' if last else ''}\n\n"
        f"{task}\n{source}\n\n"
        f"<cv_analysis>\n{analysis}\n</cv_analysis>\n\n"
        f"<historique>\n{history or 'Aucun échange pour le moment.'}\n</historique>"
    )


def next_question(
    state: dict, messages: list[tuple[str, str]], interview_type: str, difficulty: str, language: str
) -> tuple[str, dict]:
    """Génère la prochaine question (relance ou nouvelle question) et renvoie le nouvel état.

    Lève LLMError (service indisponible) ou LLMJSONError (réponse invalide).
    """
    followup_allowed = state["asked"] > 0 and not state["followup_used"]
    turn = ask_json(
        build_user_message(state, messages, interview_type, difficulty, language),
        system=load_prompt(language),
        model=RecruiterTurn,
        language=language,
        temperature=0.6,
    )

    new_state = dict(state)
    if turn.action == "followup" and followup_allowed:
        new_state["followup_used"] = True
    else:  # nouvelle question principale (une relance non autorisée compte comme telle)
        new_state["main_index"] = state["main_index"] + 1
        new_state["followup_used"] = False
    new_state["asked"] = state["asked"] + 1
    return turn.question, new_state
