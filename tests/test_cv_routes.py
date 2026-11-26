"""Tests des routes du CV : dépôt, correction, suppression (étape 4)."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import CV
from tests.helpers import register

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def create_candidate(client: TestClient, language: str = "fr") -> int:
    return register(client, language=language)


def upload(client: TestClient, candidate_id: int, name: str, data: bytes | None = None):
    content = data if data is not None else (FIXTURES_DIR / name).read_bytes()
    return client.post(
        f"/candidates/{candidate_id}/cv",
        files={"file": (name, content, "application/pdf")},
    )


def test_upload_valid_cv(client: TestClient, upload_dir: Path) -> None:
    candidate_id = create_candidate(client)
    response = upload(client, candidate_id, "cv_data_scientist_fr.pdf")

    assert response.status_code == 201
    body = response.json()
    assert "XGBoost" in body["extracted_text"]
    assert "file_path" not in body  # le chemin interne n'est pas exposé

    # Un seul fichier, renommé avec un UUID (pas le nom d'origine)
    files = list(upload_dir.iterdir())
    assert len(files) == 1
    assert files[0].name != "cv_data_scientist_fr.pdf"
    assert len(files[0].stem) == 32


def test_upload_unknown_candidate(client: TestClient) -> None:
    create_candidate(client)
    assert upload(client, 999, "cv_devops_en.pdf").status_code == 404


def test_reject_non_pdf_extension(client: TestClient) -> None:
    candidate_id = create_candidate(client)
    response = upload(client, candidate_id, "cv.docx", b"contenu")
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "not_pdf"


def test_reject_too_large_file(client: TestClient, upload_dir: Path) -> None:
    candidate_id = create_candidate(client)
    big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024)
    response = upload(client, candidate_id, "gros.pdf", big)
    assert response.status_code == 413
    assert not upload_dir.exists() or not any(upload_dir.iterdir())


def test_scanned_cv_gives_clear_message(client: TestClient, upload_dir: Path) -> None:
    candidate_id = create_candidate(client, language="en")
    response = upload(client, candidate_id, "cv_scanne.pdf")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "scanned"
    assert "scan" in detail["message"]  # message dans la langue du candidat (EN)
    assert not upload_dir.exists() or not any(upload_dir.iterdir())  # rien n'est stocké


def test_fake_pdf_is_rejected(client: TestClient) -> None:
    candidate_id = create_candidate(client)
    response = upload(client, candidate_id, "cv_invalide.pdf")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "not_pdf"


def test_candidate_corrects_text(client: TestClient) -> None:
    candidate_id = create_candidate(client)
    cv_id = upload(client, candidate_id, "cv_dev_web_fr.pdf").json()["id"]

    new_text = "Karim Benjelloun, étudiant ingénieur. Compétences : React, Node.js, SQL."
    response = client.put(f"/cvs/{cv_id}/text", json={"text": f"  {new_text}  "})
    assert response.status_code == 200
    assert client.get(f"/cvs/{cv_id}").json()["extracted_text"] == new_text


def test_corrected_text_too_short(client: TestClient) -> None:
    candidate_id = create_candidate(client)
    cv_id = upload(client, candidate_id, "cv_dev_web_fr.pdf").json()["id"]
    assert client.put(f"/cvs/{cv_id}/text", json={"text": "trop court"}).status_code == 422


def test_delete_cv_removes_file(client: TestClient, upload_dir: Path) -> None:
    candidate_id = create_candidate(client)
    cv_id = upload(client, candidate_id, "cv_marketing_en.pdf").json()["id"]

    assert client.delete(f"/cvs/{cv_id}").status_code == 204
    assert client.get(f"/cvs/{cv_id}").status_code == 404
    assert not any(upload_dir.iterdir())


def test_delete_candidate_removes_cv_files(client: TestClient, upload_dir: Path, db: Session) -> None:
    candidate_id = create_candidate(client)
    upload(client, candidate_id, "cv_devops_en.pdf")
    upload(client, candidate_id, "cv_marketing_en.pdf")
    assert len(list(upload_dir.iterdir())) == 2

    assert client.delete(f"/candidates/{candidate_id}").status_code == 204
    assert db.query(CV).count() == 0  # lignes supprimées en base
    assert not any(upload_dir.iterdir())  # fichiers PDF supprimés
    # Le compte n'existe plus : son jeton ne fonctionne plus
    assert client.get(f"/candidates/{candidate_id}").status_code == 401
