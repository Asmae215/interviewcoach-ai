
"""
InterviewCoach AI - Sélection intelligente des questions.

Fonctionnalités :
- Chargement du dataset CSV.
- Filtrage par domaine et difficulté.
- Classement selon le CV et le poste.
- Diversification des catégories.
- Conservation de la source des questions.
"""

import csv
import re
import unicodedata
from pathlib import Path


# ==========================================
# 1. CONFIGURATION DU DATASET
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    BASE_DIR / "data" / "askedbefore_cs_interview_questions.csv"
)


# ==========================================
# 2. CATÉGORIES PAR DOMAINE
# ==========================================

DOMAIN_SUBJECTS = {
    "data": [
        "Machine Learning",
        "Statistics & Analytics",
        "DBMS & SQL"
    ],

    "developpement": [
        "Programming Fundamentals",
        "OOP",
        "System Design",
        "DSA",
        "DBMS & SQL"
    ],

    "cybersecurite": [
        "Cloud & Security",
        "Computer Networks",
        "Operating Systems"
    ]
}


# ==========================================
# 3. NIVEAUX DE DIFFICULTÉ
# ==========================================

DIFFICULTY_MAP = {
    "debutant": "easy",
    "intermediaire": "medium",
    "avance": "hard"
}


# ==========================================
# 4. COMPÉTENCES ET MOTS-CLÉS
# ==========================================

SKILL_KEYWORDS = {
    "python": [
        "python"
    ],

    "sql": [
        "sql", "database", "query", "join"
    ],

    "machine learning": [
        "machine learning", "model", "training",
        "classification", "overfitting"
    ],

    "tensorflow": [
        "tensorflow", "neural network", "deep learning"
    ],

    "pandas": [
        "pandas", "dataframe", "data cleaning"
    ],

    "react": [
        "react", "frontend", "component"
    ],

    "node.js": [
        "node", "backend", "api"
    ],

    "django": [
        "django", "backend", "api"
    ],

    "postgresql": [
        "postgresql", "sql", "database", "transaction"
    ],

    "api rest": [
        "api", "rest", "http", "endpoint"
    ],

    "linux": [
        "linux", "operating system", "process"
    ],

    "wireshark": [
        "wireshark", "packet", "network", "tcp"
    ],

    "siem": [
        "siem", "security", "incident", "log", "alert"
    ],

    "tcp/ip": [
        "tcp", "ip", "network", "protocol"
    ]
}


# ==========================================
# 5. CATÉGORIES PRIORITAIRES PAR POSTE
# ==========================================

ROLE_SUBJECTS = {
    "data scientist": [
        "Machine Learning",
        "Statistics & Analytics"
    ],

    "data analyst": [
        "Statistics & Analytics",
        "DBMS & SQL"
    ],

    "data engineer": [
        "DBMS & SQL",
        "System Design"
    ],

    "full-stack": [
        "Programming Fundamentals",
        "System Design",
        "DBMS & SQL"
    ],

    "backend": [
        "System Design",
        "DBMS & SQL",
        "Programming Fundamentals"
    ],

    "frontend": [
        "Programming Fundamentals",
        "OOP"
    ],

    "soc": [
        "Cloud & Security",
        "Computer Networks"
    ],

    "cybersecurite": [
        "Cloud & Security",
        "Computer Networks"
    ]
}


# ==========================================
# 6. NORMALISATION DES TEXTES
# ==========================================

def normalize(text):
    """Met en minuscules et supprime les accents."""

    text = unicodedata.normalize("NFKD", str(text))

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    return text.lower().strip()


def contains_term(text, term):
    """Vérifie la présence d'un terme complet."""

    pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"

    return re.search(pattern, text) is not None


# ==========================================
# 7. CHARGEMENT DES QUESTIONS
# ==========================================

def load_questions():
    """Charge toutes les questions du dataset CSV."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset introuvable : {DATASET_PATH}"
        )

    with open(
        DATASET_PATH,
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as fichier:

        reader = csv.DictReader(fichier)
        questions = list(reader)

    return questions


# ==========================================
# 8. CALCUL DU SCORE DE PERTINENCE
# ==========================================

def calculate_score(question, cv_text, job_title):
    """
    Attribue un score heuristique à une question.

    Le score dépend :
    - Des catégories liées au poste.
    - Des compétences présentes dans le CV.
    - Des mots-clés retrouvés dans la question.
    """

    score = 0

    question_text = normalize(question["question"])
    cv = normalize(cv_text)
    job = normalize(job_title)

    # Bonus pour les catégories liées au poste
    for role, subjects in ROLE_SUBJECTS.items():

        if role in job and question["subject"] in subjects:
            score += 5

    # Bonus pour les compétences du CV
    for skill, keywords in SKILL_KEYWORDS.items():

        if contains_term(cv, normalize(skill)):

            for keyword in keywords:

                if contains_term(
                    question_text,
                    normalize(keyword)
                ):
                    score += 3
                    break

    return score


# ==========================================
# 9. SÉLECTION ET DIVERSIFICATION
# ==========================================

def select_questions(
    domain: str,
    difficulty: str = "intermédiaire",
    number: int = 5,
    cv_text: str = "",
    job_title: str = ""
):
    """
    Sélectionne des questions pertinentes et diversifiées.

    Étapes :
    1. Filtrer par domaine.
    2. Filtrer par difficulté.
    3. Calculer un score de pertinence.
    4. Classer les questions.
    5. Diversifier les catégories.
    6. Compléter jusqu'au nombre demandé.
    """

    domain = normalize(domain)
    level = DIFFICULTY_MAP.get(normalize(difficulty))

    if domain not in DOMAIN_SUBJECTS:
        raise ValueError(
            f"Domaine inconnu : {domain}"
        )

    if level is None:
        raise ValueError(
            f"Difficulté inconnue : {difficulty}"
        )

    if number < 1:
        raise ValueError(
            "Le nombre de questions doit être positif"
        )

    # Charger le dataset
    questions = load_questions()

    # Filtrer par domaine et difficulté
    candidates = [
        q.copy()
        for q in questions
        if q["subject"] in DOMAIN_SUBJECTS[domain]
        and normalize(q["difficulty"]) == level
        and q["question"].strip()
    ]

    # Calculer la pertinence
    for question in candidates:

        question["relevance_score"] = calculate_score(
            question=question,
            cv_text=cv_text,
            job_title=job_title
        )

    # Classer par score décroissant
    candidates.sort(
        key=lambda q: (
            -q["relevance_score"],
            q["id"]
        )
    )

    selected = []
    used_ids = set()
    used_subjects = set()

    # Première passe :
    # sélectionner différentes catégories
    for question in candidates:

        if len(selected) >= number:
            break

        if question["subject"] not in used_subjects:

            selected.append(question)

            used_subjects.add(
                question["subject"]
            )

            used_ids.add(
                question["id"]
            )

    # Deuxième passe :
    # compléter si nécessaire
    for question in candidates:

        if len(selected) >= number:
            break

        if question["id"] not in used_ids:

            selected.append(question)
            used_ids.add(
                question["id"]
            )

    return selected


# ==========================================
# 10. TEST AVEC TROIS PROFILS FICTIFS
# ==========================================

if __name__ == "__main__":

    profils = [
        {
            "domain": "data",
            "poste": "Data Scientist junior",
            "cv": (
                "Formation en Data Science. "
                "Python, SQL, Machine Learning, "
                "TensorFlow, Pandas. "
                "Projet de prédiction du risque de crédit."
            )
        },

        {
            "domain": "developpement",
            "poste": "Développeur Full-Stack junior",
            "cv": (
                "Formation en informatique. "
                "React, Node.js, Django, "
                "PostgreSQL, API REST. "
                "Projet de gestion des réservations."
            )
        },

        {
            "domain": "cybersecurite",
            "poste": "Analyste SOC junior",
            "cv": (
                "Formation en cybersécurité. "
                "Linux, Wireshark, SIEM, TCP/IP. "
                "Projet de détection d'activités suspectes."
            )
        }
    ]

    print("\n========================================")
    print(" INTERVIEWCOACH AI - SMART QUESTION TEST")
    print("========================================")

    for profil in profils:

        print("\n" + "=" * 55)
        print("POSTE :", profil["poste"])
        print("=" * 55)

        results = select_questions(
            domain=profil["domain"],
            difficulty="intermédiaire",
            number=3,
            cv_text=profil["cv"],
            job_title=profil["poste"]
        )

        if not results:
            print("Aucune question trouvée.")
            continue

        for index, question in enumerate(
            results, start=1
        ):

            print(f"\nQuestion {index}")
            print("ID :", question["id"])
            print("Sujet :", question["subject"])
            print(
                "Difficulté :",
                question["difficulty"]
            )
            print(
                "Score de pertinence :",
                question["relevance_score"]
            )
            print(
                "Question :",
                question["question"]
            )
