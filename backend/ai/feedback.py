
"""
InterviewCoach AI - Module F5
Génération du rapport final d'entretien.

Fonctionnalités :
- Calcul du score global sur 20.
- Moyenne des quatre critères d'évaluation.
- Identification des points forts.
- Identification des axes d'amélioration.
- Détection des erreurs.
- Identification des compétences à renforcer.
- Recommandations personnalisées.
- Traçabilité des questions évaluées.
"""

from datetime import datetime, timezone


# ==================================================
# 1. CRITÈRES D'ÉVALUATION
# ==================================================

CRITERIA = (
    "pertinence",
    "clarte",
    "argumentation",
    "connaissances_techniques"
)

LABELS = {
    "pertinence": "Pertinence",
    "clarte": "Clarté",
    "argumentation": "Argumentation",
    "connaissances_techniques": "Connaissances techniques"
}


# ==================================================
# 2. SUPPRESSION DES DOUBLONS
# ==================================================

def unique_texts(items):
    """
    Supprime les doublons tout en conservant
    l'ordre d'apparition des éléments.
    """

    result = []
    seen = set()

    for item in items:

        if not isinstance(item, str):
            continue

        text = item.strip()

        if text and text.casefold() not in seen:

            result.append(text)
            seen.add(text.casefold())

    return result


# ==================================================
# 3. VALIDATION DES ÉVALUATIONS
# ==================================================

def validate_evaluations(evaluated_exchanges):
    """
    Vérifie que les évaluations contiennent
    les informations nécessaires.
    """

    if not evaluated_exchanges:
        raise ValueError(
            "Aucune évaluation disponible."
        )

    for index, exchange in enumerate(
        evaluated_exchanges, start=1
    ):

        if not isinstance(exchange, dict):
            raise ValueError(
                f"Échange {index} invalide."
            )

        evaluation = exchange.get("evaluation")

        if not isinstance(evaluation, dict):
            raise ValueError(
                f"Évaluation manquante : échange {index}."
            )

        scores = evaluation.get("scores")

        if not isinstance(scores, dict):
            raise ValueError(
                f"Scores manquants : échange {index}."
            )

        for criterion in CRITERIA:

            score = scores.get(criterion)

            if type(score) is not int or not 0 <= score <= 5:
                raise ValueError(
                    f"Score invalide pour {criterion}, "
                    f"échange {index}."
                )

        for field in (
            "points_forts",
            "points_amelioration",
            "erreurs"
        ):

            value = evaluation.get(field)

            if not isinstance(value, list):
                raise ValueError(
                    f"Champ {field} invalide, "
                    f"échange {index}."
                )

        if not isinstance(
            evaluation.get("conseil"), str
        ):
            raise ValueError(
                f"Conseil invalide, échange {index}."
            )


# ==================================================
# 4. CALCUL DES MOYENNES PAR CRITÈRE
# ==================================================

def calculate_average_scores(evaluated_exchanges):
    """
    Calcule la moyenne de chaque critère
    sur l'ensemble des réponses évaluées.
    """

    averages = {}

    for criterion in CRITERIA:

        values = [
            exchange["evaluation"]["scores"][criterion]
            for exchange in evaluated_exchanges
        ]

        averages[criterion] = round(
            sum(values) / len(values),
            2
        )

    return averages


# ==================================================
# 5. IDENTIFICATION DES PRIORITÉS
# ==================================================

def identify_priorities(average_scores):
    """
    Identifie les critères ayant une moyenne
    inférieure à 3.5/5.
    """

    priorities = []

    ordered_scores = sorted(
        average_scores.items(),
        key=lambda item: item[1]
    )

    for criterion, score in ordered_scores:

        if score < 3.5:

            priorities.append({
                "critere": criterion,
                "libelle": LABELS[criterion],
                "score_sur_5": score
            })

    return priorities


# ==================================================
# 6. GÉNÉRATION DU RAPPORT FINAL
# ==================================================

def generate_feedback_report(
    evaluated_exchanges: list[dict],
    job_title: str,
    language: str = "français",
    session_id: str = ""
) -> dict:
    """
    Génère le bilan global d'un entretien à partir
    de plusieurs évaluations individuelles.

    Chaque échange doit contenir une clé "evaluation"
    avec les résultats fournis par evaluator.py.
    """

    if not isinstance(job_title, str) or not job_title.strip():
        raise ValueError(
            "Le poste recherché est obligatoire."
        )

    validate_evaluations(evaluated_exchanges)

    # ----------------------------------------------
    # A. CALCUL DES SCORES
    # ----------------------------------------------

    average_scores = calculate_average_scores(
        evaluated_exchanges
    )

    total_scores = [
        exchange["evaluation"]["scores"][criterion]
        for exchange in evaluated_exchanges
        for criterion in CRITERIA
    ]

    score_sur_20 = round(
        sum(total_scores) / len(evaluated_exchanges),
        2
    )

    score_global = round(
        score_sur_20 / 4,
        2
    )

    # ----------------------------------------------
    # B. COLLECTE DES OBSERVATIONS
    # ----------------------------------------------

    strengths = []
    improvements = []
    errors = []
    recommendations = []
    question_details = []

    for index, exchange in enumerate(
        evaluated_exchanges, start=1
    ):

        evaluation = exchange["evaluation"]

        strengths.extend(
            evaluation["points_forts"]
        )

        improvements.extend(
            evaluation["points_amelioration"]
        )

        errors.extend(
            evaluation["erreurs"]
        )

        conseil = evaluation["conseil"].strip()

        if conseil:
            recommendations.append(conseil)

        question_details.append({
            "numero": index,
            "question": exchange.get("question", ""),
            "source_id": exchange.get("source_id"),
            "type": exchange.get(
                "type", "principale"
            ),
            "score_sur_20": sum(
                evaluation["scores"].values()
            ),
            "scores": evaluation["scores"].copy()
        })

    # ----------------------------------------------
    # C. IDENTIFICATION DES PRIORITÉS
    # ----------------------------------------------

    priorities = identify_priorities(
        average_scores
    )

    skills_to_improve = [
        priority["libelle"]
        for priority in priorities
    ]

    # ----------------------------------------------
    # D. APPRÉCIATION GÉNÉRALE
    # ----------------------------------------------

    if score_sur_20 >= 16:

        appreciation = (
            "Bon résultat sur les réponses évaluées. "
            "Poursuivez votre entraînement pour "
            "consolider vos acquis."
        )

    elif score_sur_20 >= 12:

        appreciation = (
            "Résultat encourageant. Certaines réponses "
            "nécessitent davantage de précision."
        )

    else:

        appreciation = (
            "Plusieurs points sont à travailler. "
            "Un entraînement ciblé est recommandé."
        )

    # ----------------------------------------------
    # E. RAPPORT FINAL
    # ----------------------------------------------

    report = {
        "session_id": session_id,
        "job_title": job_title,
        "language": language,

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "nombre_reponses_evaluees": len(
            evaluated_exchanges
        ),

        "scores": {
            "moyennes_par_critere": average_scores,
            "score_global_sur_5": score_global,
            "score_global_sur_20": score_sur_20
        },

        "appreciation_generale": appreciation,

        "points_forts": unique_texts(
            strengths
        ),

        "axes_amelioration": unique_texts(
            improvements
        ),

        "erreurs_identifiees": unique_texts(
            errors
        ),

        "priorites": priorities,

        "competences_a_renforcer": skills_to_improve,

        "recommandations": unique_texts(
            recommendations
        ),

        "details_questions": question_details,

        "avertissement": (
            "Cette évaluation constitue une aide "
            "pédagogique. Elle ne représente pas "
            "une décision de recrutement ni une "
            "prédiction des chances d'embauche."
        )
    }

    return report
