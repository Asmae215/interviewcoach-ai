# PROGRESS — InterviewCoach AI

Étapes issues de `docs/guide_projet.pdf`. Règle d'or : ne jamais passer à l'étape suivante si la vérification échoue.

| Étape | Intitulé | Fonctionnalité | Statut | Date | Notes |
|---|---|---|---|---|---|
| 0 | Préparation des outils et du dépôt GitHub | – | ✅ fait | 2026-11-26 | Dépôt existant remis à niveau (pas de nouveau dépôt). Branche de travail : `integration/lina-ai`. `gh` non installé. |
| 1 | Structure du projet et environnement Python | – | ✅ fait | — | 6f8b065. |
| 2 | Choix et test du LLM gratuit | – | ✅ fait | — | Gemini (52b83c9), puis client unique Gemini/Groq avec secours (2f23f05). |
| 3 | Base de données et profil candidat | F1 | ✅ fait | — | ac0f213. Branche de Lina fusionnée (18dbb27) : `backend/ai/` à rebrancher sur `services/llm.py`. |
| 4 | Import du CV PDF et extraction du texte | F1, F2 | ✅ fait | 2026-11-26 | Validée par Asmae (test manuel Streamlit + /docs). | Route `POST /candidates/{id}/cv` (PDF, 5 Mo, nom UUID), correction `PUT /cvs/{id}/text`, suppression fichier + candidat. 4 CV fictifs + scanné + invalide dans `tests/fixtures/`. 19 tests pytest OK. Page Streamlit dépôt/correction. |
| 5 | Analyse du CV par le LLM | F2 | ✅ fait | 2026-11-26 | Validée par Asmae (test réel `tests.manual_cv_analysis` + Streamlit). | `POST /cvs/{id}/analyze` (consentement obligatoire côté backend), consignes `prompts/cv_analysis_{fr,en}.txt` (CV = données), JSON validé Pydantic + 2 réessais, compétences absentes du CV retirées. 31 tests pytest OK (LLM simulé). Test réel à lancer : `python -m tests.manual_cv_analysis`. Client de Lina rebranché sur `services/llm.py`. |
| 6 | Entretien avec le recruteur IA | F4 | ✅ fait | 2026-11-26 | Validée par Asmae (entretien réel FR + EN via `tests.manual_interview` et Streamlit) ; question d'ouverture corrigée (5d7afb1). | Option 1 : `services/interviewer.py` réutilise la banque de questions de Lina (`question_selector`) pour technique/mixte. 6/7/8 questions selon la difficulté, une à la fois, max 1 relance par question, analyse du CV + historique envoyés à chaque appel, messages en base. CV bloquant vérifié côté backend (409). Colonne `interviews.state` + mini-migration. 51 tests pytest OK. Test réel : `python -m tests.manual_interview`. |
| 7 | Avis du recruteur et améliorations | F5 | 🧪 en validation | 2026-11-26 | `services/evaluator.py` + `prompts/evaluator_{fr,en}.txt` : grille fixe (pertinence, clarté, argumentation, connaissances techniques) notée 1-5 avec justification obligatoire, points forts, axes d'amélioration, reformulation de la réponse la plus faible (question/réponse recopiées depuis la base), avis global. `POST/GET /interviews/{id}/report`, table `reports` (+ colonne `details`). Mention pédagogique affichée. 65 tests pytest OK. Test réel : `python -m tests.manual_evaluation`. |
| 8 | Tableau de bord et progression (+ connexion) | F7 | à faire | | |
| 9 | Tests sur scénarios prédéfinis | – | à faire | | |
| 10 | Déploiement gratuit | F8 | à faire | | |
| 11 | Documents et démonstration | – | à faire | | |
