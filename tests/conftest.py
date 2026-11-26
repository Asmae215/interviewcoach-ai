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
from backend.services import cv_storage


@pytest.fixture
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Les CV des tests vont dans un dossier temporaire, jamais dans data/uploads/."""
    folder = tmp_path / "uploads"
    monkeypatch.setattr(cv_storage, "UPLOAD_DIR", folder)
    return folder


@pytest.fixture
def client(upload_dir: Path) -> Iterator[TestClient]:
    """Client de l'API branché sur une base vide, recréée à chaque test."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db() -> Iterator[Session]:
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
