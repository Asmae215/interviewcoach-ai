"""Tests de la connexion, de l'isolation des données et du tableau de bord (étape 8)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import AuthSession, Candidate
from tests.helpers import PASSWORD, register
from tests.test_evaluator import evaluation, use_fake

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def login(client: TestClient, username: str, password: str = PASSWORD):
    return client.post("/auth/login", json={"username": username, "password": password})


def play_interviews(client: TestClient, candidate_id: int, count: int) -> list[int]:
    """Dépose et analyse un CV, puis joue `count` entretiens complets avec leur avis."""
    content = (FIXTURES_DIR / "cv_data_scientist_fr.pdf").read_bytes()
    cv = client.post(
        f"/candidates/{candidate_id}/cv", files={"file": ("cv.pdf", content, "application/pdf")}
    ).json()
    assert client.post(f"/cvs/{cv['id']}/analyze", json={"consent": True}).status_code == 200
    ids = []
    for _ in range(count):
        interview = client.post(
            f"/candidates/{candidate_id}/interviews",
            json={"interview_type": "rh", "difficulty": "debutant"},
        ).json()
        for number in range(6):
            client.post(f"/interviews/{interview['id']}/answers", json={"answer": f"Réponse {number}"})
        assert client.post(f"/interviews/{interview['id']}/report").status_code == 200
        ids.append(interview["id"])
    return ids


# --- Inscription et connexion ---

def test_register_stores_hashed_password(client: TestClient, db: Session) -> None:
    candidate_id = register(client, username="Alice")
    candidate = db.get(Candidate, candidate_id)
    assert candidate.username == "alice"  # identifiant en minuscules
    assert candidate.password_hash.startswith("pbkdf2_sha256$")
    assert PASSWORD not in candidate.password_hash
    # Seule l'empreinte du jeton est stockée
    token = client.headers["Authorization"].removeprefix("Bearer ")
    assert db.query(AuthSession).one().token_hash != token
    assert client.get("/auth/me").json()["username"] == "alice"


def test_username_must_be_unique(client: TestClient) -> None:
    register(client, username="alice")
    response = client.post(
        "/auth/register",
        json={"username": "ALICE", "password": PASSWORD, "name": "B", "target_job": "Dev",
              "level": "junior", "language": "fr"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "username_taken"


@pytest.mark.parametrize("username,password", [("a b", PASSWORD), ("ab", PASSWORD), ("alice", "court")])
def test_invalid_register_data(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/auth/register",
        json={"username": username, "password": password, "name": "A", "target_job": "Dev",
              "level": "junior", "language": "fr"},
    )
    assert response.status_code == 422


def test_login(client: TestClient) -> None:
    register(client, username="alice")
    client.headers.pop("Authorization")
    response = login(client, "alice")
    assert response.status_code == 200
    token = response.json()["token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_wrong_password_or_unknown_user(client: TestClient) -> None:
    register(client, username="alice")
    wrong = login(client, "alice", "mauvaismotdepasse")
    unknown = login(client, "personne")
    assert wrong.status_code == unknown.status_code == 401
    # Même message : on ne révèle pas si l'identifiant existe
    assert wrong.json() == unknown.json()


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer jeton-invente"}])
def test_routes_require_login(client: TestClient, headers: dict) -> None:
    for method, path in [("get", "/auth/me"), ("get", "/candidates/1"), ("get", "/cvs/1"),
                         ("get", "/interviews/1"), ("get", "/candidates/1/interviews")]:
        assert getattr(client, method)(path, headers=headers).status_code == 401


def test_logout_invalidates_token(client: TestClient) -> None:
    register(client)
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_expired_session(client: TestClient, db: Session) -> None:
    register(client)
    session = db.query(AuthSession).one()
    session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert client.get("/auth/me").status_code == 401


# --- Chaque candidat ne voit que ses données ---

def test_other_account_cannot_see_data(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    use_fake(monkeypatch, json.dumps(evaluation()))
    alice_id = register(client, username="alice")
    alice_token = client.headers["Authorization"]
    interview_id = play_interviews(client, alice_id, 1)[0]
    cv_id = client.get(f"/candidates/{alice_id}/cvs").json()[0]["id"]

    register(client, username="bob")  # le client utilise maintenant le jeton de Bob
    forbidden = [
        ("get", f"/candidates/{alice_id}"), ("patch", f"/candidates/{alice_id}"),
        ("delete", f"/candidates/{alice_id}"), ("get", f"/candidates/{alice_id}/cvs"),
        ("get", f"/candidates/{alice_id}/interviews"), ("get", f"/cvs/{cv_id}"),
        ("delete", f"/cvs/{cv_id}"), ("get", f"/interviews/{interview_id}"),
        ("delete", f"/interviews/{interview_id}"), ("get", f"/interviews/{interview_id}/report"),
    ]
    for method, path in forbidden:
        kwargs = {"json": {}} if method == "patch" else {}
        assert getattr(client, method)(path, **kwargs).status_code == 404, path
    assert client.post(f"/cvs/{cv_id}/analyze", json={"consent": True}).status_code == 404
    assert client.put(f"/cvs/{cv_id}/text", json={"text": "x" * 60}).status_code == 404
    assert client.post(f"/interviews/{interview_id}/answers", json={"answer": "x"}).status_code == 404
    assert client.post(f"/interviews/{interview_id}/report").status_code == 404
    assert client.post(
        f"/candidates/{alice_id}/interviews", json={"interview_type": "rh", "difficulty": "debutant"}
    ).status_code == 404

    # Les données d'Alice sont intactes
    client.headers["Authorization"] = alice_token
    assert client.get(f"/interviews/{interview_id}/report").status_code == 200
    assert client.get(f"/cvs/{cv_id}").status_code == 200


# --- Tableau de bord ---

def test_dashboard_shows_three_interviews(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    use_fake(monkeypatch, *[json.dumps(evaluation(score=s)) for s in (2, 3, 5)])
    alice_id = register(client, username="alice")
    ids = play_interviews(client, alice_id, 3)

    rows = client.get(f"/candidates/{alice_id}/interviews").json()
    assert [row["id"] for row in rows] == ids  # du plus ancien au plus récent
    assert [row["average"] for row in rows] == [2.0, 3.0, 5.0]  # 3 points sur le graphique
    assert rows[0]["scores"] == {
        "pertinence": 2, "clarte": 2, "argumentation": 2, "connaissances_techniques": 2,
    }
    assert all(row["status"] == "terminee" for row in rows)

    # Un autre compte ne voit pas ces entretiens
    bob_id = register(client, username="bob")
    assert client.get(f"/candidates/{bob_id}/interviews").json() == []


def test_dashboard_unfinished_interview_has_no_scores(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_fake(monkeypatch)
    alice_id = register(client)
    content = (FIXTURES_DIR / "cv_data_scientist_fr.pdf").read_bytes()
    cv = client.post(f"/candidates/{alice_id}/cv", files={"file": ("cv.pdf", content, "application/pdf")}).json()
    client.post(f"/cvs/{cv['id']}/analyze", json={"consent": True})
    client.post(f"/candidates/{alice_id}/interviews", json={"interview_type": "rh", "difficulty": "debutant"})

    row = client.get(f"/candidates/{alice_id}/interviews").json()[0]
    assert row["status"] == "en_cours"
    assert row["scores"] is None and row["average"] is None
