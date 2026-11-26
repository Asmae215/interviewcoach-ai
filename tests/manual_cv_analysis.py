"""Vérification de l'étape 5 avec le VRAI LLM, sur 3 CV fictifs.

Lancer : python -m tests.manual_cv_analysis
(Pas lancé par pytest : il consomme le quota gratuit du LLM.)
"""

import time
from pathlib import Path

from backend.services.cv_analyzer import analyze_cv
from backend.services.cv_parser import extract_text

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# (fichier, poste visé, niveau, langue)
SCENARIOS = [
    ("cv_data_scientist_fr.pdf", "Data Scientist", "junior", "fr"),
    ("cv_dev_web_fr.pdf", "Développeur full-stack", "etudiant", "fr"),  # contient une injection
    ("cv_marketing_en.pdf", "Digital Marketing Manager", "junior", "en"),
]


def main() -> None:
    for name, job, level, language in SCENARIOS:
        text = extract_text((FIXTURES_DIR / name).read_bytes())
        start = time.perf_counter()
        analysis = analyze_cv(text, job, level, language)
        duration = time.perf_counter() - start

        print(f"\n=== {name} — {job} ({language}) — {duration:.1f} s ===")
        print("Résumé      :", analysis.summary)
        print("Compétences :", ", ".join(analysis.skills))
        for exp in analysis.experiences:
            print(f"Expérience  : {exp.title} — {exp.organization} ({exp.period})")
        for edu in analysis.education:
            print(f"Formation   : {edu.degree} — {edu.school} ({edu.year})")
        for project in analysis.projects:
            print("Projet      :", project.name)
        print("Points faibles :")
        for weakness in analysis.weaknesses:
            print("  -", weakness)

        # Contrôles automatiques
        missing = [exp.organization for exp in analysis.experiences
                   if exp.organization and exp.organization not in text]
        print("✅ expériences présentes dans le CV" if not missing else f"❌ entreprises inventées : {missing}")
        print("✅ moins de 10 s" if duration < 10 else f"⚠️ {duration:.1f} s (objectif < 10 s)")
        if "5/5" in analysis.model_dump_json():
            print("❌ l'injection du CV a été suivie")


if __name__ == "__main__":
    main()
