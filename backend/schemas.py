import json
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

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


# --- Analyse du CV par le LLM (étape 5) ---

class Experience(BaseModel):
    title: str
    organization: str = ""
    period: str = ""
    highlights: list[str] = []


class Education(BaseModel):
    degree: str
    school: str = ""
    year: str = ""


class Project(BaseModel):
    name: str
    description: str = ""


class CVAnalysis(BaseModel):
    """Format JSON attendu du LLM ; toute réponse est validée avec ce modèle."""

    summary: str
    skills: list[str]
    experiences: list[Experience]
    education: list[Education]
    projects: list[Project]
    weaknesses: list[str]


class AnalyzeRequest(BaseModel):
    # Accord explicite du candidat avant l'envoi de son CV au service d'IA
    consent: bool


# --- Entretien avec le recruteur IA (étape 6) ---

InterviewType = Literal["rh", "technique", "comportemental", "mixte"]
Difficulty = Literal["debutant", "intermediaire", "avance"]


class InterviewCreate(BaseModel):
    interview_type: InterviewType
    difficulty: Difficulty


class AnswerIn(BaseModel):
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str  # "recruiter" ou "candidate"
    content: str
    position: int


class InterviewOut(BaseModel):
    id: int
    candidate_id: int
    interview_type: str
    difficulty: str
    language: str
    status: str  # "en_cours" ou "terminee"
    question_number: int  # questions déjà posées
    total_questions: int
    messages: list[MessageOut]
    created_at: datetime


class CVOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    extracted_text: str | None
    analysis: CVAnalysis | None = None
    created_at: datetime

    @field_validator("analysis", mode="before")
    @classmethod
    def parse_analysis(cls, value: object) -> object:
        """En base, l'analyse est stockée en texte JSON."""
        if isinstance(value, str):
            return json.loads(value)
        return value
