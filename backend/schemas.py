from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
