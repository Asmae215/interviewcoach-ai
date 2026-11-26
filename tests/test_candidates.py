"""Tests des routes du profil et de la suppression complète d'un compte (étape 9)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import CV, AuthSession, Candidate, Interview, Message, Report
from tests.helpers import register
from tests.test_auth import play_interviews
from tests.test_evaluator import evaluation, use_fake


def test_read_and_update_profile(client: TestClient) -> None:
    candidate_id = register(client, target_job="Data Analyst")
    assert client.get(f"/candidates/{candidate_id}").json()["target_job"] == "Data Analyst"

    response = client.patch(
        f"/candidates/{candidate_id}", json={"target_job": "Data Scientist", "language": "en"}
    )
    assert response.status_code == 200
    profile = client.get(f"/candidates/{candidate_id}").json()
    assert profile["target_job"] == "Data Scientist"
    assert profile["language"] == "en"
    assert profile["name"] == "Test"  # champ non envoyé : inchangé


@pytest.mark.parametrize("bad", [{"level": "expert"}, {"language": "de"}, {"name": ""}])
def test_invalid_profile_update(client: TestClient, bad: dict) -> None:
    candidate_id = register(client)
    assert client.patch(f"/candidates/{candidate_id}", json=bad).status_code == 422


def test_profile_never_exposes_password(client: TestClient) -> None:
    candidate_id = register(client)
    body = client.get(f"/candidates/{candidate_id}").json()
    assert "password" not in json.dumps(body)


def test_delete_account_removes_everything(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db: Session, upload_dir: Path
) -> None:
    """Confidentialité : supprimer un candidat efface ses CV (fichiers compris), entretiens,
    messages, rapports et sessions — et rien chez les autres candidats."""
    use_fake(monkeypatch, *[json.dumps(evaluation()) for _ in range(3)])
    other_id = register(client, username="autre")
    play_interviews(client, other_id, 1)
    candidate_id = register(client, username="moi")
    play_interviews(client, candidate_id, 2)
    assert len(list(upload_dir.iterdir())) == 2

    assert client.delete(f"/candidates/{candidate_id}").status_code == 204

    for model in (CV, Interview, AuthSession):
        assert db.query(model).filter_by(candidate_id=candidate_id).count() == 0
    assert db.get(Candidate, candidate_id) is None
    # Il ne reste que les données de l'autre candidat
    assert db.query(Interview).count() == 1
    assert db.query(Report).count() == 1
    assert db.query(Message).filter(Message.interview_id.notin_(
        [i.id for i in db.query(Interview).all()])).count() == 0
    assert len(list(upload_dir.iterdir())) == 1
