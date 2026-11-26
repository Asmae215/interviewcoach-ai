"""Connexion simple (étape 8) : inscription, connexion, déconnexion, candidat connecté."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuthSession, Candidate
from backend.schemas import CandidateOut, LoginIn, RegisterIn, TokenOut
from backend.services import security

router = APIRouter(prefix="/auth", tags=["auth"])

# Lit l'en-tête « Authorization: Bearer <jeton> » (et ajoute le bouton Authorize dans /docs)
bearer = HTTPBearer(auto_error=False)

MESSAGES: dict[str, dict[str, str]] = {
    "username_taken": {
        "fr": "Cet identifiant est déjà utilisé.",
        "en": "This username is already taken.",
    },
    "bad_credentials": {
        "fr": "Identifiant ou mot de passe incorrect.",
        "en": "Wrong username or password.",
    },
}

# Avant la connexion, on ne connaît pas la langue du candidat : message bilingue
AUTH_REQUIRED = {
    "code": "auth_required",
    "message": "Connecte-toi pour continuer. / Please log in to continue.",
}


def auth_error(status_code: int, code: str, language: str) -> HTTPException:
    messages = MESSAGES[code]
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": messages.get(language, messages["fr"])},
    )


def get_current_candidate(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Candidate:
    """Candidat connecté, retrouvé grâce à son jeton ; 401 si absent, inconnu ou expiré."""
    if credentials is None:
        raise HTTPException(status_code=401, detail=AUTH_REQUIRED)
    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == security.hash_token(credentials.credentials))
        .first()
    )
    if session is None or security.is_expired(session.expires_at):
        raise HTTPException(status_code=401, detail=AUTH_REQUIRED)
    return session.candidate


def open_session(db: Session, candidate: Candidate) -> TokenOut:
    """Crée une session et renvoie le jeton (seule son empreinte est stockée)."""
    token = security.new_token()
    db.add(
        AuthSession(
            candidate_id=candidate.id,
            token_hash=security.hash_token(token),
            expires_at=security.session_expiry(),
        )
    )
    db.commit()
    return TokenOut(token=token, candidate=CandidateOut.model_validate(candidate))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(Candidate).filter(Candidate.username == data.username).first():
        raise auth_error(409, "username_taken", data.language)
    candidate = Candidate(
        **data.model_dump(exclude={"username", "password"}),
        username=data.username,
        password_hash=security.hash_password(data.password),
    )
    db.add(candidate)
    try:
        db.commit()
    except IntegrityError as err:  # deux inscriptions simultanées avec le même identifiant
        db.rollback()
        raise auth_error(409, "username_taken", data.language) from err
    db.refresh(candidate)
    return open_session(db, candidate)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.username == data.username).first()
    if candidate is None or not security.verify_password(data.password, candidate.password_hash):
        # Même message dans les deux cas : on ne révèle pas si l'identifiant existe
        raise auth_error(401, "bad_credentials", data.language)
    return open_session(db, candidate)


@router.post("/logout", status_code=204)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    """Supprime la session : le jeton ne fonctionne plus."""
    if credentials is not None:
        db.query(AuthSession).filter(
            AuthSession.token_hash == security.hash_token(credentials.credentials)
        ).delete()
        db.commit()


@router.get("/me", response_model=CandidateOut)
def me(current: Candidate = Depends(get_current_candidate)):
    return current
