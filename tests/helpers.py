"""Outils partagés par les tests : créer un compte et se connecter."""

import itertools

from fastapi.testclient import TestClient

PASSWORD = "motdepasse123"
_numbers = itertools.count(1)


def register(
    client: TestClient,
    language: str = "fr",
    target_job: str = "Data Scientist",
    username: str | None = None,
) -> int:
    """Crée un compte, garde son jeton dans le client (en-tête Authorization) et renvoie l'id."""
    username = username or f"candidat{next(_numbers)}"
    response = client.post(
        "/auth/register",
        json={
            "username": username, "password": PASSWORD, "name": "Test",
            "target_job": target_job, "level": "junior", "language": language,
        },
    )
    assert response.status_code == 201, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['token']}"
    return response.json()["candidate"]["id"]
