"""Routes de l'entretien : démarrer, répondre, consulter (étape 6)."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Candidate, Interview, Message
from backend.routers.candidates import get_candidate_or_404
from backend.schemas import AnswerIn, InterviewCreate, InterviewOut, MessageOut
from backend.services import interviewer
from backend.services.llm import LLMError
from backend.services.llm_utils import LLM_ERROR_MESSAGES, LLMJSONError

router = APIRouter(tags=["interview"])

MESSAGES: dict[str, dict[str, str]] = {
    "cv_required": {
        "fr": "Dépose ton CV et fais-le analyser avant de commencer l'entretien.",
        "en": "Upload your CV and have it analysed before starting the interview.",
    },
    "interview_finished": {
        "fr": "Cet entretien est terminé.",
        "en": "This interview is over.",
    },
    **LLM_ERROR_MESSAGES,
}


def interview_error(status_code: int, code: str, language: str) -> HTTPException:
    messages = MESSAGES[code]
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": messages.get(language, messages["fr"])},
    )


def get_interview_or_404(db: Session, interview_id: int) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Entretien introuvable")
    return interview


def latest_cv_analysis(candidate: Candidate) -> dict | None:
    """Analyse du CV le plus récent ; None s'il n'y a pas de CV ou s'il n'est pas analysé."""
    if not candidate.cvs:
        return None
    latest = max(candidate.cvs, key=lambda cv: cv.id)
    return json.loads(latest.analysis) if latest.analysis else None


def generate_question(
    state: dict, history: list[tuple[str, str]], interview_type: str, difficulty: str, language: str
) -> tuple[str, dict]:
    """Appelle le recruteur IA et traduit ses erreurs en messages clairs."""
    try:
        return interviewer.next_question(state, history, interview_type, difficulty, language)
    except LLMError as err:
        raise interview_error(503, "llm_unavailable", language) from err
    except LLMJSONError as err:
        raise interview_error(502, "generation_failed", language) from err


def to_out(interview: Interview) -> InterviewOut:
    state = json.loads(interview.state or "{}")
    return InterviewOut(
        id=interview.id,
        candidate_id=interview.candidate_id,
        interview_type=interview.interview_type,
        difficulty=interview.difficulty,
        language=interview.language,
        status=interview.status,
        question_number=state.get("asked", 0),
        total_questions=state.get("total", 0),
        messages=[MessageOut.model_validate(m) for m in interview.messages],
        created_at=interview.created_at,
    )


@router.post("/candidates/{candidate_id}/interviews", response_model=InterviewOut, status_code=201)
def start_interview(candidate_id: int, data: InterviewCreate, db: Session = Depends(get_db)):
    candidate = get_candidate_or_404(db, candidate_id)
    language = candidate.language

    # CV bloquant, vérifié côté serveur : pas d'entretien sans CV analysé avec succès
    analysis = latest_cv_analysis(candidate)
    if analysis is None:
        raise interview_error(409, "cv_required", language)

    state = interviewer.build_state(
        data.interview_type, data.difficulty, candidate.target_job, candidate.level, analysis
    )
    # La première question est générée avant d'enregistrer : en cas d'erreur, rien n'est créé
    question, state = generate_question(state, [], data.interview_type, data.difficulty, language)

    interview = Interview(
        candidate_id=candidate.id,
        interview_type=data.interview_type,
        difficulty=data.difficulty,
        language=language,
        status="en_cours",
        state=json.dumps(state, ensure_ascii=False),
    )
    interview.messages.append(Message(role="recruiter", content=question, position=0))
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return to_out(interview)


@router.post("/interviews/{interview_id}/answers", response_model=InterviewOut)
def answer_question(interview_id: int, data: AnswerIn, db: Session = Depends(get_db)):
    interview = get_interview_or_404(db, interview_id)
    language = interview.language
    if interview.status != "en_cours":
        raise interview_error(409, "interview_finished", language)

    state = json.loads(interview.state)
    history = [(m.role, m.content) for m in interview.messages] + [("candidate", data.answer)]

    if interviewer.is_finished(state):
        # Réponse à la dernière question : on clôt l'entretien (pas d'appel au LLM)
        reply = interviewer.CLOSING_MESSAGE[language]
        interview.status = "terminee"
    else:
        # Si le LLM échoue, la réponse n'est pas enregistrée : le candidat peut la renvoyer
        reply, state = generate_question(
            state, history, interview.interview_type, interview.difficulty, language
        )

    position = len(interview.messages)
    interview.messages.append(Message(role="candidate", content=data.answer, position=position))
    interview.messages.append(Message(role="recruiter", content=reply, position=position + 1))
    interview.state = json.dumps(state, ensure_ascii=False)
    db.commit()
    db.refresh(interview)
    return to_out(interview)


@router.get("/interviews/{interview_id}", response_model=InterviewOut)
def read_interview(interview_id: int, db: Session = Depends(get_db)):
    return to_out(get_interview_or_404(db, interview_id))
