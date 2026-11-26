"""Stockage des CV déposés dans data/uploads/ sous un nom généré (UUID)."""

import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


def save_cv_file(data: bytes) -> str:
    """Enregistre le PDF sous un nom aléatoire et renvoie ce nom (jamais le nom d'origine)."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / name).write_bytes(data)
    return name


def delete_cv_file(name: str) -> None:
    """Supprime le fichier du CV s'il existe encore."""
    (UPLOAD_DIR / Path(name).name).unlink(missing_ok=True)
