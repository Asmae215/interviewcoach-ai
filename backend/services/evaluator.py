"""Avis du recruteur (étape 7) : évaluation de tout l'entretien avec une grille fixe."""

import json
from pathlib import Path

from backend.schemas import Evaluation
from backend.services.cv_analyzer import LEVEL_LABELS
from backend.services.interviewer import DIFFICULTY_LABELS, TYPE_LABELS
from backend.services.llm_utils import ask_json, strip_data_tags

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

CRITERIA = ("pertinence", "clarte", "argumentation", "connaissances_techniques")

DISCLAIMER = {
    "fr": "Ces scores sont pédagogiques : ils servent à t'entraîner et ne constituent pas une décision de recrutement.",
    "en": "These scores are for practice only: they are not a hiring decision.",
}


def load_prompt(language: str) -> str:
    return (PROMPTS_DIR / f"evaluator_{language}.txt").read_text(encoding="utf-8")


def exchanges_from(messages: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Paires (question du recruteur, réponse du candidat) ; le message de clôture est ignoré."""
    pairs = []
    for current, following in zip(messages, messages[1:]):
        if current[0] == "recruiter" and following[0] == "candidate":
            pairs.append((current[1], following[1]))
    return pairs


def build_user_message(
    exchanges: list[tuple[str, str]],
    state: dict,
    interview_type: str,
    difficulty: str,
    language: str,
) -> str:
    """Contexte de l'entretien + transcription numérotée (réponses balisées comme données)."""
    analysis = state.get("cv_analysis", {})
    context = {"summary": analysis.get("summary", ""), "skills": analysis.get("skills", [])}
    context_json = strip_data_tags(json.dumps(context, ensure_ascii=False))
    level = LEVEL_LABELS[language].get(state.get("level", ""), state.get("level", ""))

    if language == "en":
        label, question_label, answer_label, tag, answer_tag = "Exchange", "Question", "Answer", "interview", "answer"
        header = (
            f"Target job: {state.get('target_job', '')}\nCandidate level: {level}\n"
            f"Interview type: {TYPE_LABELS['en'][interview_type]}\n"
            f"Difficulty: {DIFFICULTY_LABELS['en'][difficulty]}\n"
            f"Number of exchanges: {len(exchanges)}"
        )
    else:
        label, question_label, answer_label, tag, answer_tag = "Échange", "Question", "Réponse", "entretien", "reponse"
        header = (
            f"Poste visé : {state.get('target_job', '')}\nNiveau du candidat : {level}\n"
            f"Type d'entretien : {TYPE_LABELS['fr'][interview_type]}\n"
            f"Difficulté : {DIFFICULTY_LABELS['fr'][difficulty]}\n"
            f"Nombre d'échanges : {len(exchanges)}"
        )

    blocks = []
    for number, (question, answer) in enumerate(exchanges, start=1):
        blocks.append(
            f"{label} {number}\n{question_label} : {strip_data_tags(question)}\n"
            f"{answer_label} : <{answer_tag}>{strip_data_tags(answer)}</{answer_tag}>"
        )
    transcript = "\n\n".join(blocks)
    return (
        f"{header}\n\n<cv_analysis>\n{context_json}\n</cv_analysis>\n\n"
        f"<{tag}>\n{transcript}\n</{tag}>"
    )


def evaluate_interview(
    messages: list[tuple[str, str]],
    state: dict,
    interview_type: str,
    difficulty: str,
    language: str,
) -> dict:
    """Évalue l'entretien et renvoie le rapport complet (dict prêt à enregistrer).

    Lève LLMError (service indisponible) ou LLMJSONError (JSON toujours invalide).
    """
    exchanges = exchanges_from(messages)
    if not exchanges:
        raise ValueError("Aucune réponse à évaluer")

    evaluation = ask_json(
        build_user_message(exchanges, state, interview_type, difficulty, language),
        system=load_prompt(language),
        model=Evaluation,
        language=language,
        temperature=0.2,
    )

    # La question et la réponse la plus faible sont recopiées depuis la base, pas depuis le LLM
    index = evaluation.weakest_answer.index
    if not 1 <= index <= len(exchanges):  # numéro impossible : on prend la réponse la plus courte
        index = min(range(len(exchanges)), key=lambda i: len(exchanges[i][1])) + 1
    question, answer = exchanges[index - 1]

    report = evaluation.model_dump()
    report["weakest_answer"].update({"index": index, "question": question, "answer": answer})
    return report


def average_score(report: dict) -> float:
    return round(sum(report["scores"][c]["score"] for c in CRITERIA) / len(CRITERIA), 1)
