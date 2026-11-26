"""Tableau de bord (étape 8) : liste des entretiens du candidat connecté avec leurs notes."""

import json

from fastapi import APIRouter, Depends

from backend.models import Candidate, Interview
from backend.routers.auth import get_current_candidate
from backend.routers.candidates import get_own_candidate
from backend.schemas import InterviewSummary
from backend.services.evaluator import CRITERIA

router = APIRouter(tags=["dashboard"])


def summarize(interview: Interview) -> InterviewSummary:
    state = json.loads(interview.state or "{}")
    scores = None
    average = None
    if interview.report is not None and interview.report.scores:
        scores = json.loads(interview.report.scores)
        average = round(sum(scores[c] for c in CRITERIA) / len(CRITERIA), 1)
    return InterviewSummary(
        id=interview.id,
        interview_type=interview.interview_type,
        difficulty=interview.difficulty,
        language=interview.language,
        status=interview.status,
        question_number=state.get("asked", 0),
        total_questions=state.get("total", 0),
        created_at=interview.created_at,
        scores=scores,
        average=average,
    )


@router.get("/candidates/{candidate_id}/interviews", response_model=list[InterviewSummary])
def list_interviews(candidate_id: int, current: Candidate = Depends(get_current_candidate)):
    """Entretiens du plus ancien au plus récent (ordre du graphique de progression)."""
    candidate = get_own_candidate(candidate_id, current)
    interviews = sorted(candidate.interviews, key=lambda i: (i.created_at, i.id))
    return [summarize(interview) for interview in interviews]
