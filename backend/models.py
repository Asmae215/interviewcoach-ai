from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    target_job: Mapped[str] = mapped_column(String(150))
    level: Mapped[str] = mapped_column(String(30))
    language: Mapped[str] = mapped_column(String(2), default="fr")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    cvs: Mapped[list["CV"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    interviews: Mapped[list["Interview"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    file_path: Mapped[str] = mapped_column(String(300))
    extracted_text: Mapped[str | None] = mapped_column(Text, default=None)
    analysis: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    candidate: Mapped["Candidate"] = relationship(back_populates="cvs")


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    interview_type: Mapped[str] = mapped_column(String(30))
    difficulty: Mapped[str] = mapped_column(String(30))
    language: Mapped[str] = mapped_column(String(2), default="fr")
    status: Mapped[str] = mapped_column(String(20), default="en_cours")
    # Progression de l'entretien en JSON (questions posées, relance, analyse du CV utilisée)
    state: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    candidate: Mapped["Candidate"] = relationship(back_populates="interviews")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="Message.position",
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="interview", cascade="all, delete-orphan", uselist=False
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)

    interview: Mapped["Interview"] = relationship(back_populates="messages")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"))
    scores: Mapped[str | None] = mapped_column(Text, default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    improvements: Mapped[str | None] = mapped_column(Text, default=None)
    # Rapport complet en JSON (justifications, points forts, reformulation...)
    details: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    interview: Mapped["Interview"] = relationship(back_populates="report")
