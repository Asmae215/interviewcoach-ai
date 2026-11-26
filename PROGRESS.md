# PROGRESS — InterviewCoach AI

> Intitulés provisoires, à aligner sur `docs/guide_projet.pdf` dès que le PDF est ajouté dans `docs/`.

| Étape | Intitulé | Statut | Date | Notes |
|---|---|---|---|---|
| 0 | Mise en place (Git, GitHub, .gitignore, .env.example) | ✅ fait | 2026-11-26 | Dépôt existant remis à niveau (pas de nouveau dépôt). Branche de travail : `integration/lina-ai`. `gh` non installé. |
| 1 | Structure du projet et environnement Python | ✅ fait | — | Commit « Structure initiale du projet » (6f8b065). |
| 2 | Connexion au LLM | ✅ fait | — | Gemini (52b83c9), puis client unique Gemini/Groq avec secours (2f23f05). |
| 3 | Base de données SQLite et profil candidat (F1) | ✅ fait | — | ac0f213. Branche IA de Lina fusionnée (18dbb27) : `backend/ai/` à intégrer dans `services/` (un seul `llm.py`). |
| 4 | Upload et extraction du CV PDF (F1) | à faire | | |
| 5 | Analyse du CV (F2) | à faire | | |
| 6 | Entretien avec le recruteur IA (F4) | à faire | | |
| 7 | Évaluation et avis (F5) | à faire | | |
| 8 | Frontend Streamlit et tableau de bord (F7) | à faire | | |
| 9 | Tests pytest | à faire | | |
| 10 | Docker et déploiement (F8) | à faire | | |
| 11 | README, diagrammes et remise | à faire | | |
