"""Profil du candidat connecté : lire, modifier, supprimer (le compte se crée via /auth/register)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Candidate
from backend.routers.auth import get_current_candidate
from backend.schemas import CandidateOut, CandidateUpdate
from backend.services.cv_storage import delete_cv_file

router = APIRouter(prefix="/candidates", tags=["candidates"])


def get_own_candidate(candidate_id: int, current: Candidate) -> Candidate:
    """Chaque candidat ne voit que ses données : un autre identifiant donne 404."""
    if candidate_id != current.id:
        raise HTTPException(status_code=404, detail="Candidat introuvable")
    return current


@router.get("/{candidate_id}", response_model=CandidateOut)
def read_candidate(candidate_id: int, current: Candidate = Depends(get_current_candidate)):
    return get_own_candidate(candidate_id, current)


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: int,
    data: CandidateUpdate,
    db: Session = Depends(get_db),
    current: Candidate = Depends(get_current_candidate),
):
    candidate = get_own_candidate(candidate_id, current)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current: Candidate = Depends(get_current_candidate),
):
    candidate = get_own_candidate(candidate_id, current)
    # Les lignes (CV, entretiens, rapports, sessions) partent en cascade ; les fichiers PDF aussi
    cv_files = [cv.file_path for cv in candidate.cvs]
    db.delete(candidate)
    db.commit()
    for name in cv_files:
        delete_cv_file(name)
