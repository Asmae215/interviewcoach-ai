"""Tests du choix de la base : SQLite en local, PostgreSQL (Neon) en production (étape 10)."""

import pytest
from sqlalchemy import create_engine

from backend.database import database_url


def test_sqlite_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url().startswith("sqlite:///")
    assert database_url().endswith("interviewcoach.db")


@pytest.mark.parametrize("given", [
    "postgresql://user:pw@ep-test.neon.tech/neondb?sslmode=require",
    "postgres://user:pw@ep-test.neon.tech/neondb?sslmode=require",
])
def test_neon_url_uses_psycopg(monkeypatch: pytest.MonkeyPatch, given: str) -> None:
    monkeypatch.setenv("DATABASE_URL", given)
    url = database_url()
    assert url == "postgresql+psycopg://user:pw@ep-test.neon.tech/neondb?sslmode=require"
    # Le pilote est bien installé (aucune connexion n'est ouverte ici)
    assert create_engine(url).dialect.driver == "psycopg"


def test_spaces_around_url_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "   ")
    assert database_url().startswith("sqlite:///")
