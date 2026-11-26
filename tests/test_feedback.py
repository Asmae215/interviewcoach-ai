
"""
InterviewCoach AI - Tests du module Feedback F5

Objectifs :
- Vérifier le calcul du score global.
- Vérifier les moyennes des quatre critères.
- Vérifier les points forts.
- Vérifier les axes d'amélioration.
- Vérifier les recommandations.
- Vérifier la traçabilité des questions.
- Vérifier la gestion des données invalides.
"""

import json
import pytest

from backend.ai.feedback import generate_feedback_report


# ==================================================
# 1. DONNÉES DE TEST
# ==================================================

EVALUATIONS = [
    {
        "question": "Qu'est-ce qu'un CNN ?",
        "source_id": "ab-0509",
        "type": "principale",
        "evaluation": {
            "scores": {
                "pertinence": 5,
                "clarte": 5,
                "argumentation": 4,
                "connaissances_techniques": 5
            },
            "points_forts": [
                "Bonne compréhension des CNN."
            ],
            "points_amelioration": [
                "Donner un exemple d'application."
            ],
            "erreurs": [],
            "conseil": (
                "Présenter un exemple concret "
                "d'utilisation des CNN."
            )
        }
    },
    {
        "question": "Expliquez le théorème central limite.",
        "source_id": "ab-0580",
        "type": "principale",
        "evaluation": {
            "scores": {
                "pertinence": 3,
                "clarte": 4,
                "argumentation": 2,
                "connaissances_techniques": 3
            },
            "points_forts": [
                "Explication compréhensible."
            ],
            "points_amelioration": [
                "Préciser les conditions d'application."
            ],
            "erreurs": [],
            "conseil": (
                "Réviser les hypothèses du théorème "
                "central limite et pratiquer des exemples."
            )
        }
    }
]


# ==================================================
# 2. TEST DU SCORE GLOBAL
# ==================================================

def test_score_global():

    report = generate_feedback_report(
        evaluated_exchanges=EVALUATIONS,
        job_title="Data Scientist junior",
        language="français",
        session_id="test-session"
    )

    assert report["nombre_reponses_evaluees"] == 2

    assert report["scores"]["score_global_sur_20"] == 15.5

    assert report["scores"]["score_global_sur_5"] == 3.88

    print("\nTEST SCORE GLOBAL : REUSSI")


# ==================================================
# 3. TEST DES MOYENNES PAR CRITÈRE
# ==================================================

def test_moyennes_criteres():

    report = generate_feedback_report(
        evaluated_exchanges=EVALUATIONS,
        job_title="Data Scientist junior"
    )

    averages = report["scores"]["moyennes_par_critere"]

    assert averages["pertinence"] == 4.0
    assert averages["clarte"] == 4.5
    assert averages["argumentation"] == 3.0

    assert averages["connaissances_techniques"] == 4.0

    print("\nTEST MOYENNES : REUSSI")


# ==================================================
# 4. TEST DES POINTS FORTS
# ==================================================

def test_points_forts():

    report = generate_feedback_report(
        evaluated_exchanges=EVALUATIONS,
        job_title="Data Scientist junior"
    )

    strengths = report["points_forts"]

    assert len(strengths) == 2

    assert "Bonne compréhension des CNN." in strengths

    assert "Explication compréhensible." in strengths

    print("\nTEST POINTS FORTS : REUSSI")


# ==================================================
# 5. TEST DES AXES D'AMÉLIORATION
# ==================================================

def test_axes_amelioration():

    report = generate_feedback_report(
        evaluated_exchanges=EVALUATIONS,
        job_title="Data Scientist junior"
    )

    improvements = report["axes_amelioration"]

    assert len(improvements) == 2

    assert "Donner un exemple d'application." in improvements

    assert (
        "Préciser les conditions d'application."
        in improvements
    )

    print("\nTEST AXES D'AMELIORATION : REUSSI")


# ==================================================
# 6. TEST DES RECOMMANDATIONS
# ==================================================

def test_recommandations():

    report = generate_feedback_report(
        evaluated_exchanges=EVALUATIONS,
        job_title="Data Scientist junior"
    )

    recommendations = report["recommandations"]

    assert len(recommendations) == 2

    assert any(
        "CNN" in recommendation
        for recommendation in recommendations
    )

    print("\nTEST RECOMMANDATIONS : REUSSI")


# ==================================================
# 7. TEST DES PRIORITÉS
# ==================================================

def test_priorites():

    report = generate_feedback_report(
        evaluated_exchanges=EVALUATIONS,
        job_title="Data Scientist junior"
    )

    priorities = report["priorites"]

    assert len(priorities) == 1

    assert priorities[0]["critere"] == "argumentation"

    assert priorities[0]["score_sur_5"] == 3.0

    print("\nTEST PRIORITES : REUSSI")


# ==================================================
# 8. TEST DE LA TRAÇABILITÉ
# ==================================================

def test_tracabilite_questions():

    report = generate_feedback_report(
        evaluated_exchanges=EVALUATIONS,
        job_title="Data Scientist junior"
    )

    details = report["details_questions"]

    assert len(details) == 2

    assert details[0]["source_id"] == "ab-0509"

    assert details[1]["source_id"] == "ab-0580"

    assert details[0]["score_sur_20"] == 19

    assert details[1]["score_sur_20"] == 12

    print("\nTEST TRACABILITE : REUSSI")


# ==================================================
# 9. TEST : AUCUNE ÉVALUATION
# ==================================================

def test_evaluations_vides():

    with pytest.raises(ValueError):

        generate_feedback_report(
            evaluated_exchanges=[],
            job_title="Data Scientist junior"
        )

    print("\nTEST EVALUATIONS VIDES : REUSSI")


# ==================================================
# 10. TEST : SCORE INVALIDE
# ==================================================

def test_score_invalide():

    invalid_evaluations = [
        {
            "question": "Qu'est-ce que SQL ?",
            "evaluation": {
                "scores": {
                    "pertinence": 8,
                    "clarte": 5,
                    "argumentation": 4,
                    "connaissances_techniques": 5
                },
                "points_forts": [],
                "points_amelioration": [],
                "erreurs": [],
                "conseil": "Réviser SQL."
            }
        }
    ]

    with pytest.raises(ValueError):

        generate_feedback_report(
            evaluated_exchanges=invalid_evaluations,
            job_title="Data Scientist junior"
        )

    print("\nTEST SCORE INVALIDE : REUSSI")


# ==================================================
# 11. AFFICHAGE DU RAPPORT COMPLET
# ==================================================

def test_rapport_complet():

    report = generate_feedback_report(
        evaluated_exchanges=EVALUATIONS,
        job_title="Data Scientist junior",
        language="français",
        session_id="test-session"
    )

    assert report["session_id"] == "test-session"

    assert report["job_title"] == "Data Scientist junior"

    assert report["nombre_reponses_evaluees"] == 2

    print("\n" + "=" * 60)
    print("RAPPORT FINAL INTERVIEWCOACH AI")
    print("=" * 60)

    print(
        json.dumps(
            report,
            indent=4,
            ensure_ascii=False
        )
    )

    print("\nTEST RAPPORT COMPLET : REUSSI")
