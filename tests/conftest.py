"""Fixtures pytest : base SQLite en mémoire et dossier d'upload temporaire."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.services import cv_storage, security


@pytest.fixture(autouse=True)
def fast_password_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hash rapide pendant les tests (600 000 itérations ralentiraient chaque inscription)."""
    monkeypatch.setattr(security, "ITERATIONS", 1_000)


@pytest.fixture
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Les CV des tests vont dans un dossier temporaire, jamais dans data/uploads/."""
    folder = tmp_path / "uploads"
    monkeypatch.setattr(cv_storage, "UPLOAD_DIR", folder)
    return folder


@pytest.fixture
def test_sessionmaker() -> Iterator[sessionmaker]:
    """Base SQLite vide en mémoire, recréée à chaque test."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture
def db(test_sessionmaker: sessionmaker) -> Iterator[Session]:
    """Accès direct à la base de test, pour vérifier ce qui est réellement stocké."""
    session = test_sessionmaker()
    yield session
    session.close()


@pytest.fixture
def client(upload_dir: Path, test_sessionmaker: sessionmaker) -> Iterator[TestClient]:
    """Client de l'API branché sur la base de test."""

    def override_get_db() -> Iterator[Session]:
        session = test_sessionmaker()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
