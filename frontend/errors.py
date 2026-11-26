"""Traduction des erreurs de validation de l'API (Pydantic) en messages clairs, FR ou EN."""

FIELD_LABELS = {
    "fr": {
        "username": "Identifiant", "password": "Mot de passe", "name": "Nom",
        "target_job": "Poste visé", "level": "Niveau", "language": "Langue",
        "text": "Texte du CV", "answer": "Réponse",
        "interview_type": "Type d'entretien", "difficulty": "Difficulté",
    },
    "en": {
        "username": "Username", "password": "Password", "name": "Name",
        "target_job": "Target job", "level": "Level", "language": "Language",
        "text": "CV text", "answer": "Answer",
        "interview_type": "Interview type", "difficulty": "Difficulty",
    },
}

MESSAGES = {
    "fr": {
        "missing": "champ obligatoire",
        "string_too_short": "au moins {min_length} caractères",
        "string_too_long": "au plus {max_length} caractères",
        "string_pattern_mismatch": "seulement des lettres, des chiffres, le point, le tiret et le tiret bas",
        "default": "valeur non valide",
    },
    "en": {
        "missing": "required field",
        "string_too_short": "at least {min_length} characters",
        "string_too_long": "at most {max_length} characters",
        "string_pattern_mismatch": "only letters, digits, dot, hyphen and underscore",
        "default": "invalid value",
    },
}


def format_validation_errors(errors: list[dict], language: str = "fr") -> str:
    """Transforme la liste d'erreurs de FastAPI en phrase lisible, ex. « Identifiant : au moins 3 caractères »."""
    labels = FIELD_LABELS.get(language, FIELD_LABELS["fr"])
    messages = MESSAGES.get(language, MESSAGES["fr"])
    parts = []
    for error in errors:
        field = str(error.get("loc", ["?"])[-1])
        kind = error.get("type", "")
        context = error.get("ctx") or {}
        if kind == "string_too_short" and context.get("min_length") == 1:
            kind = "missing"  # un champ vide : « champ obligatoire » est plus clair
        template = messages.get(kind, messages["default"])
        try:
            text = template.format(**context)
        except (KeyError, IndexError):
            text = messages["default"]
        parts.append(f"{labels.get(field, field)} : {text}")
    return " ; ".join(parts) if parts else messages["default"]
