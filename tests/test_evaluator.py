
"""
InterviewCoach AI - Test de l'évaluateur F5.

Objectifs :
- Comparer trois qualités de réponses.
- Vérifier les scores attribués.
- Examiner les justifications.
- Détecter les éventuelles incohérences.
"""

from backend.ai.evaluator import evaluate_answer


QUESTION = (
    "Quelle est la différence entre "
    "INNER JOIN et LEFT JOIN ?"
)

JOB_TITLE = "Data Scientist junior"


# ==========================================
# 1. TROIS RÉPONSES DE QUALITÉ DIFFÉRENTE
# ==========================================

TEST_CASES = [
    {
        "name": "RÉPONSE CORRECTE",
        "answer": (
            "INNER JOIN retourne uniquement les lignes "
            "qui possèdent une correspondance dans les "
            "deux tables. LEFT JOIN conserve toutes les "
            "lignes de la table de gauche et ajoute les "
            "correspondances de droite. Lorsqu'aucune "
            "correspondance n'existe, les colonnes de "
            "droite contiennent des valeurs NULL."
        )
    },
    {
        "name": "RÉPONSE PARTIELLE",
        "answer": (
            "INNER JOIN permet de combiner deux tables. "
            "LEFT JOIN permet aussi de combiner des tables, "
            "mais je ne connais pas exactement la différence."
        )
    },
    {
        "name": "RÉPONSE INCORRECTE",
        "answer": (
            "INNER JOIN supprime définitivement les lignes "
            "sans correspondance dans la base de données, "
            "tandis que LEFT JOIN ajoute automatiquement "
            "de nouvelles lignes dans la table de gauche."
        )
    }
]


# ==========================================
# 2. TEST DES ÉVALUATIONS
# ==========================================

def tester_evaluateur():

    print("\n" + "=" * 60)
    print("INTERVIEWCOACH AI - TEST EVALUATEUR F5")
    print("=" * 60)

    results = []

    for case in TEST_CASES:

        print("\n" + "-" * 60)
        print(case["name"])
        print("-" * 60)

        try:
            result = evaluate_answer(
                question=QUESTION,
                answer=case["answer"],
                job_title=JOB_TITLE,
                language="français",
                question_type="technique"
            )

            evaluation = result["evaluation"]
            scores = evaluation["scores"]

            print("\nSCORES :")

            for criterion, score in scores.items():
                print(f"- {criterion}: {score}/5")

            print(
                "\nSCORE GLOBAL :",
                evaluation["score_sur_20"],
                "/20"
            )

            print("\nJUSTIFICATIONS :")

            for criterion, justification in (
                evaluation["justifications"].items()
            ):
                print(
                    f"- {criterion}: {justification}"
                )

            print("\nERREURS IDENTIFIÉES :")

            for error in evaluation["erreurs"]:
                print("-", error)

            print("\nCONSEIL :")
            print(evaluation["conseil"])

            results.append({
                "name": case["name"],
                "score": evaluation["score_sur_20"]
            })

        except Exception as error:
            print(
                f"Erreur : {type(error).__name__} - {error}"
            )

    return results


# ==========================================
# 3. COMPARAISON DES SCORES
# ==========================================

if __name__ == "__main__":

    results = tester_evaluateur()

    if len(results) == 3:

        print("\n" + "=" * 60)
        print("COMPARAISON FINALE")
        print("=" * 60)

        for result in results:
            print(
                f"{result['name']} : "
                f"{result['score']}/20"
            )

        scores = [result["score"] for result in results]

        if scores[0] > scores[1] > scores[2]:
            print(
                "\nTEST DE CLASSEMENT : RÉUSSI"
            )
        else:
            print(
                "\nTEST DE CLASSEMENT : À EXAMINER"
            )

    else:
        print(
            "\nCertains tests ont échoué : "
            "comparaison incomplète."
        )
