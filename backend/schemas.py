from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Level = Literal["etudiant", "junior", "confirme"]
Language = Literal["fr", "en"]


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_job: str = Field(min_length=1, max_length=150)
    level: Level
    language: Language = "fr"


class CandidateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    target_job: str | None = Field(default=None, min_length=1, max_length=150)
    level: Level | None = None
    language: Language | None = None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target_job: str
    level: str
    language: str
    created_at: datetime


# Texte du CV corrigé par le candidat (espaces retirés au début et à la fin)
CVText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=50, max_length=50_000)
]


class CVTextUpdate(BaseModel):
    text: CVText


class CVOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    extracted_text: str | None
    created_at: datetime
