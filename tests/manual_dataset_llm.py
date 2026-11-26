
"""Test d'intégration Dataset + LLM - InterviewCoach AI."""

from backend.ai.question_selector import select_questions
from backend.ai.prompts import create_dataset_question_prompt
from backend.ai.llm_client import generate_response


PROFILS = [
    {
        "domain": "data",
        "job_title": "Data Scientist junior",
        "cv_text": (
            "Formation en Data Science. "
            "Compétences : Python, SQL, Machine Learning. "
            "Projet : prédiction du risque de crédit."
        )
    },
    {
        "domain": "developpement",
        "job_title": "Développeur Full-Stack junior",
        "cv_text": (
            "Compétences : React, Django, PostgreSQL. "
            "Projet : application de gestion des "
            "réservations avec API REST."
        )
    },
    {
        "domain": "cybersecurite",
        "job_title": "Analyste SOC junior",
        "cv_text": (
            "Compétences : Linux, SIEM, Wireshark. "
            "Projet : analyse de journaux réseau "
            "pour détecter des activités suspectes."
        )
    }
]


def tester_integration():

    print("\n=== INTERVIEWCOACH AI : DATASET + LLM ===")

    for profil in PROFILS:

        print("\n" + "=" * 60)
        print("POSTE :", profil["job_title"])
        print("=" * 60)

        questions = select_questions(
            domain=profil["domain"],
            difficulty="intermédiaire",
            number=1,
            cv_text=profil["cv_text"],
            job_title=profil["job_title"]
        )

        if not questions:
            print("Aucune question trouvée.")
            continue

        question_source = questions[0]

        prompt = create_dataset_question_prompt(
            source_question=question_source["question"],
            cv_text=profil["cv_text"],
            job_title=profil["job_title"],
            difficulty="intermédiaire",
            language="français"
        )

        try:
            question_finale = generate_response(prompt)

            print("\nID source :", question_source["id"])
            print("Catégorie :", question_source["subject"])
            print(
                "Question originale :",
                question_source["question"]
            )

            print("\nQUESTION PERSONNALISÉE :")
            print(question_finale)

        except Exception as erreur:
            print(
                f"Erreur : {type(erreur).__name__} - {erreur}"
            )


if __name__ == "__main__":
    tester_integration()
