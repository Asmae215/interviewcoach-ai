"""Mots de passe hashés (PBKDF2, bibliothèque standard) et jetons de session (étape 8)."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

ITERATIONS = 600_000  # recommandation OWASP pour PBKDF2-SHA256
SESSION_DAYS = 7


def hash_password(password: str) -> str:
    """Renvoie « algo$itérations$sel$hash » : le mot de passe n'est jamais stocké en clair."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Compare en temps constant le mot de passe saisi avec le hash enregistré."""
    try:
        algorithm, iterations, salt_hex, digest_hex = (stored or "").split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def new_token() -> str:
    """Jeton aléatoire remis au candidat à la connexion."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """En base, on ne garde que l'empreinte du jeton (comme pour un mot de passe)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)


def is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:  # SQLite renvoie des dates sans fuseau (stockées en UTC)
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < datetime.now(timezone.utc)
