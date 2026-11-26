"""Tests de l'extraction du texte des CV (étape 4)."""

from pathlib import Path

import pytest

from backend.services.cv_parser import CVParseError, clean_text, extract_text

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Pour chaque CV fictif, des passages qui doivent se retrouver dans le texte extrait
EXPECTED = {
    "cv_data_scientist_fr.pdf": ["Yasmine Alaoui", "Expériences", "XGBoost", "Scikit-learn"],
    "cv_dev_web_fr.pdf": ["Karim Benjelloun", "React", "Génie Informatique"],
    "cv_marketing_en.pdf": ["Emily Carter", "Google Analytics", "Mailchimp"],
    "cv_devops_en.pdf": ["Thomas Moreau", "Kubernetes", "Terraform"],
}


@pytest.mark.parametrize("name,passages", EXPECTED.items())
def test_fake_cvs_are_extracted(name: str, passages: list[str]) -> None:
    text = extract_text((FIXTURES_DIR / name).read_bytes())
    for passage in passages:
        assert passage in text


def assert_error(data: bytes, code: str) -> None:
    with pytest.raises(CVParseError) as info:
        extract_text(data)
    assert info.value.code == code


def test_scanned_pdf_is_detected() -> None:
    assert_error((FIXTURES_DIR / "cv_scanne.pdf").read_bytes(), "scanned")


def test_fake_pdf_is_rejected() -> None:
    assert_error((FIXTURES_DIR / "cv_invalide.pdf").read_bytes(), "not_pdf")


def test_empty_file_is_rejected() -> None:
    assert_error(b"", "empty_file")


def test_damaged_pdf_is_unreadable() -> None:
    assert_error(b"%PDF-1.4\n" + b"\x00\xff garbage " * 50, "unreadable")


def test_clean_text_normalizes_spaces() -> None:
    raw = "  Python   et\tSQL  \r\n\r\n\r\n\r\nGit avancé  "
    assert clean_text(raw) == "Python et SQL\n\nGit avancé"
