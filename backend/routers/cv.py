"""Routes du CV : dépôt du PDF, lecture, correction du texte, suppression (étape 4)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CV
from backend.routers.candidates import get_candidate_or_404
from backend.schemas import AnalyzeRequest, CVOut, CVTextUpdate
from backend.services import cv_analyzer
from backend.services.cv_parser import CVParseError, error_message, extract_text
from backend.services.cv_storage import delete_cv_file, save_cv_file
from backend.services.llm import LLMError

router = APIRouter(tags=["cv"])

MAX_CV_SIZE = 5 * 1024 * 1024  # 5 Mo


def cv_error(status_code: int, code: str, language: str) -> HTTPException:
    """Erreur avec un code stable (pour le frontend) et un message lisible."""
    if code in cv_analyzer.MESSAGES:
        messages = cv_analyzer.MESSAGES[code]
        message = messages.get(language, messages["fr"])
    else:
        message = error_message(code, language)
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def get_cv_or_404(db: Session, cv_id: int) -> CV:
    cv = db.get(CV, cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV introuvable")
    return cv


@router.post("/candidates/{candidate_id}/cv", response_model=CVOut, status_code=201)
async def upload_cv(
    candidate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    candidate = get_candidate_or_404(db, candidate_id)
    language = candidate.language

    if not (file.filename or "").lower().endswith(".pdf"):
        raise cv_error(415, "not_pdf", language)

    # On lit au plus 5 Mo + 1 octet : suffisant pour savoir si c'est trop gros
    data = await file.read(MAX_CV_SIZE + 1)
    if len(data) > MAX_CV_SIZE:
        raise cv_error(413, "too_large", language)

    # Le texte est extrait avant d'enregistrer : un PDF invalide n'est jamais stocké
    try:
        text = extract_text(data)
    except CVParseError as err:
        raise cv_error(422, err.code, language) from err

    cv = CV(candidate_id=candidate.id, file_path=save_cv_file(data), extracted_text=text)
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.get("/cvs/{cv_id}", response_model=CVOut)
def read_cv(cv_id: int, db: Session = Depends(get_db)):
    return get_cv_or_404(db, cv_id)


@router.put("/cvs/{cv_id}/text", response_model=CVOut)
def update_cv_text(cv_id: int, data: CVTextUpdate, db: Session = Depends(get_db)):
    """Le candidat corrige le texte extrait ; l'ancienne analyse n'est plus valable."""
    cv = get_cv_or_404(db, cv_id)
    cv.extracted_text = data.text
    cv.analysis = None
    db.commit()
    db.refresh(cv)
    return cv


@router.post("/cvs/{cv_id}/analyze", response_model=CVOut)
def analyze_cv(cv_id: int, data: AnalyzeRequest, db: Session = Depends(get_db)):
    """Envoie le texte du CV au LLM (avec l'accord du candidat) et enregistre l'analyse."""
    cv = get_cv_or_404(db, cv_id)
    candidate = cv.candidate
    language = candidate.language

    # Consentement vérifié côté serveur : sans accord, rien n'est envoyé au LLM
    if not data.consent:
        raise cv_error(403, "consent_required", language)
    if not cv.extracted_text:
        raise cv_error(422, "no_text", language)

    try:
        analysis = cv_analyzer.analyze_cv(
            cv.extracted_text, candidate.target_job, candidate.level, language
        )
    except LLMError as err:
        raise cv_error(503, "llm_unavailable", language) from err
    except cv_analyzer.CVAnalysisError as err:
        raise cv_error(502, "analysis_failed", language) from err

    cv.analysis = analysis.model_dump_json()
    db.commit()
    db.refresh(cv)
    return cv


@router.delete("/cvs/{cv_id}", status_code=204)
def delete_cv(cv_id: int, db: Session = Depends(get_db)):
    cv = get_cv_or_404(db, cv_id)
    file_name = cv.file_path
    db.delete(cv)
    db.commit()
    delete_cv_file(file_name)
