
"""Test du recruteur IA sur plusieurs domaines professionnels."""

from backend.ai.llm_client import generate_response
from backend.ai.prompts import create_recruiter_prompt


# ==========================================
# 1. PROFILS FICTIFS DES CANDIDATS
# ==========================================

profils = [
    {
        "domaine": "DATA",
        "poste": "Data Scientist junior",
        "cv": """
        Formation : Ingénierie Data Science et IA.
        Compétences : Python, SQL, Pandas,
        Scikit-learn, TensorFlow.
        Projet : Prédiction du risque de crédit
        avec des algorithmes de Machine Learning.
        Expérience : Stage en analyse de données.
        """,
        "type": "technique"
    },
    {
        "domaine": "DÉVELOPPEMENT",
        "poste": "Développeur Full-Stack junior",
        "cv": """
        Formation : Ingénierie informatique.
        Compétences : JavaScript, React, Node.js,
        Python, Django et PostgreSQL.
        Projet : Application web de gestion
        des réservations avec API REST.
        Expérience : Stage en développement web.
        """,
        "type": "technique"
    },
    {
        "domaine": "CYBERSÉCURITÉ",
        "poste": "Analyste SOC junior",
        "cv": """
        Formation : Informatique et cybersécurité.
        Compétences : Réseaux TCP/IP, Linux,
        Wireshark, SIEM et analyse des logs.
        Projet : Détection d'activités suspectes
        dans des journaux réseau.
        Expérience : Stage en administration réseau.
        """,
        "type": "technique"
    }
]


# ==========================================
# 2. TEST DE PERSONNALISATION
# ==========================================

def tester_profils():

    print("\n====================================")
    print(" INTERVIEWCOACH AI - TEST MULTI-JOBS")
    print("====================================")

    for profil in profils:

        print("\n" + "=" * 55)
        print("DOMAINE :", profil["domaine"])
        print("POSTE :", profil["poste"])
        print("=" * 55)

        prompt = create_recruiter_prompt(
            cv_text=profil["cv"],
            job_title=profil["poste"],
            interview_type=profil["type"],
            difficulty="intermédiaire",
            language="français"
        )

        try:
            question = generate_response(prompt)

            print("\nQUESTION DU RECRUTEUR IA :\n")
            print(question)

        except Exception as erreur:
            print(f"\nErreur : {type(erreur).__name__}")
            print(str(erreur))


# ==========================================
# 3. EXÉCUTION
# ==========================================

if __name__ == "__main__":
    tester_profils()
