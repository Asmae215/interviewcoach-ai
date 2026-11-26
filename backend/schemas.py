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
    username: str | None = None
    name: str
    target_job: str
    level: str
    language: str
    created_at: datetime


# --- Connexion (étape 8) ---

# Identifiant : lettres, chiffres, point, tiret, tiret bas ; enregistré en minuscules
# (le format est vérifié avant la mise en minuscules, d'où A-Z dans le motif)
Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, min_length=3, max_length=50,
        pattern=r"^[A-Za-z0-9._-]+$",
    ),
]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class RegisterIn(CandidateCreate):
    username: Username
    password: Password


class LoginIn(BaseModel):
    username: Username
    password: Password
    language: Language = "fr"  # langue des messages d'erreur


class TokenOut(BaseModel):
    token: str
    candidate: CandidateOut


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


# --- Avis du recruteur et améliorations (étape 7) ---

class CriterionScore(BaseModel):
    score: int = Field(ge=1, le=5)
    justification: str = Field(min_length=10)  # justification obligatoire


class Scores(BaseModel):
    """Grille fixe d'évaluation."""

    pertinence: CriterionScore
    clarte: CriterionScore
    argumentation: CriterionScore
    connaissances_techniques: CriterionScore


class WeakestAnswer(BaseModel):
    index: int  # numéro de l'échange (1 = première question)
    why: str = Field(min_length=10)
    improved_answer: str = Field(min_length=20)  # reformulation suggérée


class Evaluation(BaseModel):
    """Format JSON attendu de l'évaluateur ; toute réponse est validée avec ce modèle."""

    scores: Scores
    strengths: list[str] = Field(min_length=1, max_length=5)
    improvements: list[str] = Field(min_length=1, max_length=6)
    weakest_answer: WeakestAnswer
    overall_feedback: str = Field(min_length=20)


class WeakestAnswerOut(WeakestAnswer):
    question: str
    answer: str


class ReportOut(BaseModel):
    interview_id: int
    scores: Scores
    average: float
    strengths: list[str]
    improvements: list[str]
    weakest_answer: WeakestAnswerOut
    overall_feedback: str
    disclaimer: str  # « scores pédagogiques, pas une décision de recrutement »
    created_at: datetime


# --- Tableau de bord (étape 8) ---

class InterviewSummary(BaseModel):
    """Une ligne du tableau de bord : un entretien et ses notes (si l'avis existe)."""

    id: int
    interview_type: str
    difficulty: str
    language: str
    status: str
    question_number: int
    total_questions: int
    created_at: datetime
    scores: dict[str, int] | None = None  # notes par critère
    average: float | None = None


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
