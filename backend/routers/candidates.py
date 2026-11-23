from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Candidate
from backend.schemas import CandidateCreate, CandidateOut, CandidateUpdate

router = APIRouter(prefix="/candidates", tags=["candidates"])


def get_candidate_or_404(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidat introuvable")
    return candidate


@router.post("", response_model=CandidateOut, status_code=201)
def create_candidate(data: CandidateCreate, db: Session = Depends(get_db)):
    candidate = Candidate(**data.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("", response_model=list[CandidateOut])
def list_candidates(db: Session = Depends(get_db)):
    return db.query(Candidate).order_by(Candidate.id).all()


@router.get("/{candidate_id}", response_model=CandidateOut)
def read_candidate(candidate_id: int, db: Session = Depends(get_db)):
    return get_candidate_or_404(db, candidate_id)


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: int, data: CandidateUpdate, db: Session = Depends(get_db)
):
    candidate = get_candidate_or_404(db, candidate_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = get_candidate_or_404(db, candidate_id)
    db.delete(candidate)
    db.commit()
