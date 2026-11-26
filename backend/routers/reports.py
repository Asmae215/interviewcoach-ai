"""Routes du rapport : générer et lire l'avis du recruteur (étape 7)."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Candidate, Report
from backend.routers.auth import get_current_candidate
from backend.routers.interview import get_interview_or_404
from backend.schemas import ReportOut
from backend.services import evaluator
from backend.services.llm import LLMError
from backend.services.llm_utils import LLM_ERROR_MESSAGES, LLMJSONError

router = APIRouter(tags=["reports"])

MESSAGES: dict[str, dict[str, str]] = {
    "interview_not_finished": {
        "fr": "L'avis est disponible une fois l'entretien terminé.",
        "en": "Feedback is available once the interview is over.",
    },
    "report_not_found": {
        "fr": "Aucun avis n'a encore été généré pour cet entretien.",
        "en": "No feedback has been generated for this interview yet.",
    },
    **LLM_ERROR_MESSAGES,
}


def report_error(status_code: int, code: str, language: str) -> HTTPException:
    messages = MESSAGES[code]
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": messages.get(language, messages["fr"])},
    )


def to_out(report: Report, language: str) -> ReportOut:
    details = json.loads(report.details)
    return ReportOut(
        interview_id=report.interview_id,
        scores=details["scores"],
        average=evaluator.average_score(details),
        strengths=details["strengths"],
        improvements=details["improvements"],
        weakest_answer=details["weakest_answer"],
        overall_feedback=details["overall_feedback"],
        disclaimer=evaluator.DISCLAIMER.get(language, evaluator.DISCLAIMER["fr"]),
        created_at=report.created_at,
    )


@router.post("/interviews/{interview_id}/report", response_model=ReportOut)
def create_report(
    interview_id: int,
    db: Session = Depends(get_db),
    current: Candidate = Depends(get_current_candidate),
):
    """Génère l'avis à la fin de l'entretien (une seule fois : ensuite, renvoie le même)."""
    interview = get_interview_or_404(db, interview_id, current)
    language = interview.language
    if interview.report is not None:
        return to_out(interview.report, language)
    if interview.status != "terminee":
        raise report_error(409, "interview_not_finished", language)

    messages = [(m.role, m.content) for m in interview.messages]
    try:
        details = evaluator.evaluate_interview(
            messages, json.loads(interview.state), interview.interview_type,
            interview.difficulty, language,
        )
    except LLMError as err:
        raise report_error(503, "llm_unavailable", language) from err
    except LLMJSONError as err:
        raise report_error(502, "generation_failed", language) from err

    report = Report(
        interview_id=interview.id,
        # Notes seules : utilisées par le tableau de bord (étape 8)
        scores=json.dumps({c: details["scores"][c]["score"] for c in evaluator.CRITERIA}),
        summary=details["overall_feedback"],
        improvements=json.dumps(details["improvements"], ensure_ascii=False),
        details=json.dumps(details, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return to_out(report, language)


@router.get("/interviews/{interview_id}/report", response_model=ReportOut)
def read_report(
    interview_id: int,
    db: Session = Depends(get_db),
    current: Candidate = Depends(get_current_candidate),
):
    interview = get_interview_or_404(db, interview_id, current)
    if interview.report is None:
        raise report_error(404, "report_not_found", interview.language)
    return to_out(interview.report, interview.language)
