"""Extraction et nettoyage du texte d'un CV PDF (étape 4)."""

import re
from io import BytesIO

from pypdf import PdfReader

# En dessous de ce nombre de caractères, on considère qu'il n'y a pas de vrai texte
MIN_TEXT_CHARS = 50

# Messages d'erreur clairs, dans la langue du candidat
MESSAGES: dict[str, dict[str, str]] = {
    "empty_file": {
        "fr": "Le fichier est vide.",
        "en": "The file is empty.",
    },
    "not_pdf": {
        "fr": "Le fichier n'est pas un PDF. Dépose ton CV au format PDF.",
        "en": "The file is not a PDF. Please upload your CV as a PDF.",
    },
    "too_large": {
        "fr": "Le fichier dépasse 5 Mo. Dépose un PDF plus léger.",
        "en": "The file is larger than 5 MB. Please upload a smaller PDF.",
    },
    "unreadable": {
        "fr": "Le PDF est illisible ou endommagé. Réexporte-le puis réessaie.",
        "en": "The PDF is unreadable or damaged. Export it again and retry.",
    },
    "encrypted": {
        "fr": "Le PDF est protégé par un mot de passe. Retire la protection puis réessaie.",
        "en": "The PDF is password-protected. Remove the protection and retry.",
    },
    "scanned": {
        "fr": (
            "Aucun texte n'a pu être extrait : le PDF est probablement scanné "
            "(image). Exporte ton CV en PDF depuis Word ou Google Docs."
        ),
        "en": (
            "No text could be extracted: the PDF is probably a scan (image). "
            "Export your CV as a PDF from Word or Google Docs."
        ),
    },
}


def error_message(code: str, language: str = "fr") -> str:
    """Renvoie le message d'erreur dans la langue demandée (français par défaut)."""
    messages = MESSAGES[code]
    return messages.get(language, messages["fr"])


class CVParseError(Exception):
    """Erreur d'extraction du CV, identifiée par un code (voir MESSAGES)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def clean_text(raw: str) -> str:
    """Normalise les espaces et les sauts de ligne du texte extrait."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "").replace(" ", " ")
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)  # au plus une ligne vide d'affilée
    return text.strip()


def extract_text(data: bytes) -> str:
    """Extrait le texte nettoyé d'un PDF. Lève CVParseError en cas d'échec."""
    if not data:
        raise CVParseError("empty_file")
    if b"%PDF-" not in data[:1024]:
        raise CVParseError("not_pdf")

    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise CVParseError("encrypted")
        pages = [page.extract_text() or "" for page in reader.pages]
    except CVParseError:
        raise
    except Exception as exc:  # pypdf lève des erreurs variées sur un fichier abîmé
        raise CVParseError("unreadable") from exc

    text = clean_text("\n\n".join(pages))
    if len(text) < MIN_TEXT_CHARS:
        raise CVParseError("scanned")
    return text
