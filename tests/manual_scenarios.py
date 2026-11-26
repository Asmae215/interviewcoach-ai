"""Étape 9 — tests sur scénarios prédéfinis avec le VRAI LLM, puis écriture de docs/rapport_tests.md.

Lancer : python -m tests.manual_scenarios
(Pas lancé par pytest : environ 60 appels au LLM, compter 3 à 6 minutes selon le quota.)

Le script :
1. lance pytest et note le résultat ;
2. joue 5 entretiens complets (poste, langue, type, difficulté différents) et vérifie
   que les questions citent le CV, respectent la langue et ne se répètent pas ;
3. compare l'évaluation de l'IA avec les notes humaines de tests/scenarios/jugement.csv ;
4. mesure tous les temps de génération (objectif < 10 s).
"""

import csv
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from backend.ai.question_selector import contains_term, normalize
from backend.services import interviewer
from backend.services.cv_analyzer import analyze_cv
from backend.services.cv_parser import extract_text
from backend.services.evaluator import CRITERIA, average_score, evaluate_interview
from backend.services.llm import LLMError
from backend.services.llm_utils import LLMJSONError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"
JUDGEMENT_FILE = ROOT / "tests" / "scenarios" / "jugement.csv"
REPORT_FILE = ROOT / "docs" / "rapport_tests.md"

SCENARIOS = [
    {"id": "S1", "cv": "cv_data_scientist_fr.pdf", "job": "Data Scientist", "level": "junior",
     "type": "technique", "difficulty": "intermediaire", "language": "fr"},
    {"id": "S2", "cv": "cv_dev_web_fr.pdf", "job": "Développeur full-stack", "level": "etudiant",
     "type": "mixte", "difficulty": "debutant", "language": "fr"},  # CV avec une injection cachée
    {"id": "S3", "cv": "cv_marketing_en.pdf", "job": "Digital Marketing Manager", "level": "junior",
     "type": "comportemental", "difficulty": "debutant", "language": "en"},
    {"id": "S4", "cv": "cv_devops_en.pdf", "job": "Senior DevOps Engineer", "level": "confirme",
     "type": "technique", "difficulty": "avance", "language": "en"},
    {"id": "S5", "cv": "cv_data_scientist_fr.pdf", "job": "Data Analyst", "level": "junior",
     "type": "rh", "difficulty": "intermediaire", "language": "en"},  # CV en français, entretien en anglais
]

# Réponses génériques du candidat (moyennes, ni vides ni parfaites) ; une est volontairement vague
ANSWERS = {
    "fr": [
        "Je suis en fin de formation et j'ai fait un stage où j'ai travaillé sur un projet concret lié à ce poste.",
        "J'ai utilisé les outils indiqués sur mon CV.",
        "J'ai d'abord analysé le besoin avec l'équipe, puis j'ai testé deux solutions et gardé la plus simple à maintenir ; le résultat a été validé par mon tuteur.",
        "Je commencerais par vérifier les données et les hypothèses, puis je mesurerais le résultat avec un indicateur clair.",
        "Quand j'ai rencontré un problème, j'ai demandé conseil, documenté la solution et partagé ce que j'avais appris avec l'équipe.",
        "Je veux progresser sur ce métier et prendre plus de responsabilités dans des projets en production.",
        "Je m'organise avec une liste de priorités et je fais un point régulier avec l'équipe.",
        "Je pense que ma rigueur et ma curiosité sont mes principaux atouts pour ce poste.",
    ],
    "en": [
        "I am finishing my degree and I did an internship where I worked on a real project related to this job.",
        "I used the tools listed on my CV.",
        "First I analysed the need with the team, then I tested two solutions and kept the simplest one to maintain; my manager validated the result.",
        "I would start by checking the data and the assumptions, then measure the result with a clear indicator.",
        "When I faced a problem, I asked for advice, documented the solution and shared what I learned with the team.",
        "I want to grow in this job and take on more responsibility in production projects.",
        "I organise my work with a priority list and regular check-ins with the team.",
        "I think my rigour and curiosity are my main strengths for this position.",
    ],
}

FR_WORDS = {"vous", "votre", "vos", "le", "la", "les", "des", "est", "pour", "avec", "comment", "quel", "quelle", "dans", "une"}
EN_WORDS = {"you", "your", "the", "what", "how", "with", "which", "is", "for", "did", "would", "can", "a", "an"}

RESULTS_FILE = ROOT / "tests" / "scenarios" / "derniers_resultats.json"

# Tous les temps de génération (s), par type : question, analyse, avis
durations: dict[str, list[float]] = {"question": [], "analyse": [], "avis": []}
TIME_LABELS = {
    "question": "Questions du recruteur",
    "analyse": "Analyse du CV",
    "avis": "Avis du recruteur",
}


def timed(kind: str, function, *args):
    start = time.perf_counter()
    result = function(*args)
    duration = time.perf_counter() - start
    durations[kind].append(duration)
    return result, duration


def detect_language(text: str) -> str:
    words = re.findall(r"[a-zà-ÿ']+", text.lower())
    french = sum(word in FR_WORDS for word in words)
    english = sum(word in EN_WORDS for word in words)
    return "fr" if french >= english else "en"


def cv_terms(analysis: dict) -> set[str]:
    """Éléments du CV qu'une question personnalisée peut citer.

    Chaque élément est aussi découpé aux virgules, parenthèses et tirets :
    « Application de covoiturage étudiant (React + Express) » donne aussi
    « Application de covoiturage étudiant », que le recruteur cite sans la parenthèse.
    """
    items = list(analysis.get("skills", []))
    for exp in analysis.get("experiences", []):
        items += [exp.get("organization", ""), exp.get("title", "")]
    for edu in analysis.get("education", []):
        items += [edu.get("school", ""), edu.get("degree", "")]
    items += [project.get("name", "") for project in analysis.get("projects", [])]

    terms = set()
    for item in items:
        for part in [item, *re.split(r"[,()/—–]| - ", item)]:
            part = normalize(part).strip(" .:")
            if len(part) >= 3:
                terms.add(part)
    return terms


def cites_cv(question: str, terms: set[str]) -> bool:
    """Mot entier seulement : « css » ne doit pas être trouvé dans « accessibilité »."""
    text = normalize(question)
    return any(contains_term(text, term) for term in terms)


def run_pytest() -> str:
    # pytest.ini ajoute déjà -q ; un second -q masquerait la ligne de résumé
    result = subprocess.run(
        [sys.executable, "-m", "pytest"], cwd=ROOT, capture_output=True, text=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else "pytest n'a rien affiché"


def run_scenario(scenario: dict) -> dict:
    language = scenario["language"]
    text = extract_text((FIXTURES_DIR / scenario["cv"]).read_bytes())
    analysis_model, analysis_time = timed(
        "analyse", analyze_cv, text, scenario["job"], scenario["level"], language
    )
    analysis = analysis_model.model_dump()
    state = interviewer.build_state(
        scenario["type"], scenario["difficulty"], scenario["job"], scenario["level"], analysis
    )

    history: list[tuple[str, str]] = []
    turns = []
    answers = iter(ANSWERS[language])
    while not interviewer.is_finished(state):
        (question, new_state), duration = timed(
            "question", interviewer.next_question, state, history,
            scenario["type"], scenario["difficulty"], language,
        )
        kind = "relance" if new_state["followup_used"] else "question"
        state = new_state
        answer = next(answers, ANSWERS[language][-1])
        history += [("recruiter", question), ("candidate", answer)]
        turns.append({"kind": kind, "question": question, "answer": answer, "time": duration})
    history.append(("recruiter", interviewer.CLOSING_MESSAGE[language]))

    report, evaluation_time = timed(
        "avis", evaluate_interview, history, state, scenario["type"], scenario["difficulty"], language
    )

    terms = cv_terms(analysis)
    questions = [turn["question"] for turn in turns]
    times = [turn["time"] for turn in turns]
    return {
        **scenario,
        "total": state["total"],
        "asked": len(questions),
        "followups": sum(turn["kind"] == "relance" for turn in turns),
        "cv_cited": sum(cites_cv(q, terms) for q in questions),
        "language_ok": all(detect_language(q) == language for q in questions),
        "repeats": len(questions) - len(set(questions)),
        "avg_time": statistics.mean(times),
        "max_time": max(times),
        "analysis_time": analysis_time,
        "evaluation_time": evaluation_time,
        "average": average_score(report),
        "turns": turns,
        "skills": analysis["skills"],
        "analysis": analysis,
    }


def run_judgement() -> list[dict]:
    """Chaque réponse est évaluée seule (un entretien d'un seul échange)."""
    with JUDGEMENT_FILE.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    state = {"target_job": "Data Scientist", "level": "junior",
             "cv_analysis": {"summary": "Data scientist junior.", "skills": []}}
    results = []
    for row in rows:
        messages = [("recruiter", row["question"]), ("candidate", row["reponse"])]
        try:
            report, _ = timed("avis", evaluate_interview, messages, state, "mixte", "intermediaire", "fr")
            model_score = average_score(report)
        except (LLMError, LLMJSONError) as error:
            print(f"  {row['id']} : échec ({error})")
            model_score = None
        results.append({**row, "note_humaine": int(row["note_humaine"]), "note_ia": model_score})
        print(f"  {row['id']} : humain {row['note_humaine']} / IA {model_score}")
    return results


def mark(ok: bool) -> str:
    return "✅" if ok else "❌"


def write_report(pytest_line: str, scenarios: list[dict], judgement: list[dict]) -> None:
    provider = os.getenv("LLM_PROVIDER", "gemini")
    model = os.getenv("GEMINI_MODEL" if provider == "gemini" else "GROQ_MODEL", "(valeur par défaut)")
    lines = [
        "# Rapport de tests — InterviewCoach AI",
        "",
        f"Généré le {datetime.now():%d/%m/%Y à %H:%M} par `python -m tests.manual_scenarios`.",
        f"Fournisseur LLM principal : **{provider}** (`{model}`), secours automatique sur l'autre fournisseur.",
        "",
        "## 1. Tests automatiques (pytest)",
        "",
        f"Résultat : **{pytest_line}** (LLM simulé, aucun appel réseau).",
        "",
        "| Fichier | Ce qui est vérifié |",
        "|---|---|",
        "| `test_cv_parser.py` | Extraction des 4 CV fictifs, PDF scanné, faux PDF, fichier vide, PDF abîmé |",
        "| `test_cv_routes.py` | Dépôt (PDF seul, 5 Mo max, nom UUID), correction du texte, suppression des fichiers |",
        "| `test_cv_analyzer.py` | Consentement obligatoire, JSON validé + réessais, compétences inventées retirées |",
        "| `test_interviewer.py` | CV bloquant, 6/7/8 questions, une relance max, historique envoyé, injection bloquée |",
        "| `test_evaluator.py` | Grille 1-5, justification obligatoire, réessais, avis unique, mention pédagogique |",
        "| `test_auth.py` | Mot de passe hashé, sessions, isolation des comptes, tableau de bord (3 entretiens = 3 points) |",
        "| `test_candidates.py` | Profil, suppression complète d'un compte (CV, fichiers, entretiens, rapports, sessions) |",
        "",
        "## 2. Scénarios d'entretien (vrai LLM)",
        "",
        "Critère d'acceptation n°4 : au moins 5 questions adaptées au CV, dans la langue, le type et la difficulté choisis.",
        "Une question « cite le CV » si elle contient une compétence, une entreprise, un diplôme, un établissement ou un projet de l'analyse.",
        "",
        "| # | Poste | Langue | Type | Difficulté | Questions | Relances | Citent le CV | Langue respectée | Répétitions | Temps moyen / max | Analyse CV | Avis | Moyenne de l'avis | Adapté au CV (≥ 5) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in scenarios:
        if "error" in s:
            lines.append(f"| {s['id']} | {s['job']} | {s['language']} | {s['type']} | {s['difficulty']} | ❌ échec : {s['error']} |" + " |" * 9)
            continue
        lines.append(
            f"| {s['id']} | {s['job']} | {s['language']} | {s['type']} | {s['difficulty']} "
            f"| {s['asked']}/{s['total']} | {s['followups']} | {s['cv_cited']}/{s['asked']} "
            f"| {mark(s['language_ok'])} | {s['repeats']} | {s['avg_time']:.1f} s / {s['max_time']:.1f} s "
            f"| {s['analysis_time']:.1f} s | {s['evaluation_time']:.1f} s | {s['average']}/5 "
            f"| {mark(s['cv_cited'] >= 5)} |"
        )
    lines += ["", "Transcriptions (réponses du candidat écrites d'avance, donc pas toujours en phase avec la question) :", ""]
    for s in scenarios:
        if "error" in s:
            continue
        lines += [f"<details><summary>{s['id']} — {s['job']} ({s['language']}, {s['type']}, {s['difficulty']})</summary>", "",
                  f"Compétences retenues par l'analyse : {', '.join(s['skills'])}", ""]
        for number, turn in enumerate(s["turns"], start=1):
            label = "Relance" if turn["kind"] == "relance" else "Question"
            lines += [f"{number}. **{label}** ({turn['time']:.1f} s) : {turn['question']}", f"   - *Candidat* : {turn['answer']}"]
        lines += ["", "</details>", ""]

    lines += [
        "## 3. Évaluation de l'IA comparée au jugement humain",
        "",
        "Chaque réponse est évaluée seule par l'évaluateur (moyenne des 4 critères) et comparée à la note humaine "
        "de `tests/scenarios/jugement.csv`.",
        "",
        "| # | Question | Réponse (début) | Note humaine | Note IA | Écart |",
        "|---|---|---|---|---|---|",
    ]
    pairs = [(row["note_humaine"], row["note_ia"]) for row in judgement if row["note_ia"] is not None]
    for row in judgement:
        answer = row["reponse"][:70] + ("…" if len(row["reponse"]) > 70 else "")
        if row["note_ia"] is None:
            lines.append(f"| {row['id']} | {row['question']} | {answer} | {row['note_humaine']} | échec | — |")
        else:
            gap = row["note_ia"] - row["note_humaine"]
            lines.append(f"| {row['id']} | {row['question']} | {answer} | {row['note_humaine']} | {row['note_ia']} | {gap:+.1f} |")
    if len(pairs) >= 2:
        humans, models = zip(*pairs)
        mae = statistics.mean(abs(m - h) for h, m in pairs)
        within_one = sum(abs(m - h) <= 1 for h, m in pairs) / len(pairs)
        correlation = statistics.correlation(humans, models)
        lines += [
            "",
            f"- Écart moyen absolu : **{mae:.2f} point**",
            f"- Réponses à 1 point ou moins de la note humaine : **{within_one:.0%}** ({sum(abs(m - h) <= 1 for h, m in pairs)}/{len(pairs)})",
            f"- Corrélation (Pearson) entre notes humaines et notes IA : **{correlation:.2f}**",
        ]

    lines += [
        "", "## 4. Temps de réponse", "",
        "Objectif du cahier des charges : moins de 10 s pour une question ou une réponse, hors incident "
        "réseau ou indisponibilité du modèle.",
        "",
        "| Type | Générations | Moyenne | Médiane | 90 % sous | Maximum | Sous 10 s |",
        "|---|---|---|---|---|---|---|",
    ]
    for kind, values in durations.items():
        if not values:
            continue
        ordered = sorted(values)
        p90 = ordered[max(0, int(len(ordered) * 0.9) - 1)]
        under_10 = sum(v < 10 for v in values)
        lines.append(
            f"| {TIME_LABELS[kind]} | {len(values)} | {statistics.mean(values):.1f} s "
            f"| {statistics.median(values):.1f} s | {p90:.1f} s | {max(values):.1f} s "
            f"| {under_10}/{len(values)} |"
        )
    lines += [
        "",
        "Les temps incluent les réessais automatiques (limite de quota gratuit, JSON invalide) et le passage "
        "au fournisseur de secours. Ce test enchaîne une soixantaine d'appels en quelques minutes, plus vite "
        "qu'un vrai candidat : les limites du quota gratuit y sont plus souvent atteintes.",
    ]

    ok_scenarios = [s for s in scenarios if "error" not in s]
    lines += [
        "",
        "## 5. Bilan",
        "",
        f"- {mark('failed' not in pytest_line and 'error' not in pytest_line)} Tests automatiques : {pytest_line}",
        f"- {mark(len(ok_scenarios) == len(scenarios))} Scénarios terminés : {len(ok_scenarios)}/{len(scenarios)}",
        f"- {mark(all(s['cv_cited'] >= 5 for s in ok_scenarios))} Au moins 5 questions citant le CV dans chaque scénario",
        f"- {mark(all(s['language_ok'] for s in ok_scenarios))} Langue respectée dans toutes les questions",
        f"- {mark(all(s['repeats'] == 0 for s in ok_scenarios))} Aucune question répétée",
    ]
    if len(pairs) >= 2:
        lines.append(f"- {mark(mae <= 1)} Évaluation proche du jugement humain (écart moyen ≤ 1 point)")
    if durations["question"]:
        worst = max(durations["question"])
        lines.append(f"- {mark(worst < 10)} Questions du recruteur sous 10 s (maximum {worst:.1f} s)")
    long_ones = durations["analyse"] + durations["avis"]
    if long_ones:
        slow = sum(v >= 10 for v in long_ones)
        symbol = "✅" if slow == 0 else "⚠️"
        lines.append(
            f"- {symbol} Analyse du CV et avis final (générations longues, une seule fois par CV ou par entretien) : "
            f"{len(long_ones) - slow}/{len(long_ones)} sous 10 s, maximum {max(long_ones):.1f} s"
        )
    lines += ["", "> Les scores sont pédagogiques et ne constituent pas une décision de recrutement.", ""]

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print("1/3 — pytest…")
    pytest_line = run_pytest()
    print("   ", pytest_line)

    print("2/3 — 5 scénarios d'entretien…")
    scenarios = []
    for scenario in SCENARIOS:
        try:
            result = run_scenario(scenario)
            print(f"   {scenario['id']} : {result['asked']} questions, {result['cv_cited']} citent le CV, "
                  f"max {result['max_time']:.1f} s")
        except (LLMError, LLMJSONError) as error:
            result = {**scenario, "error": str(error)[:120]}
            print(f"   {scenario['id']} : échec — {error}")
        scenarios.append(result)

    print("3/3 — évaluation IA vs jugement humain…")
    judgement = run_judgement()

    # Résultats bruts : permettent de recalculer le rapport sans rappeler le LLM
    RESULTS_FILE.write_text(
        json.dumps({"pytest": pytest_line, "scenarios": scenarios, "judgement": judgement,
                    "durations": durations}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    write_report(pytest_line, scenarios, judgement)
    print(f"\nRapport écrit dans {REPORT_FILE}")


def rebuild() -> None:
    """Réécrit le rapport à partir des derniers résultats bruts (aucun appel au LLM)."""
    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    durations.update(data["durations"])
    for scenario in data["scenarios"]:
        if "error" not in scenario:
            terms = cv_terms(scenario["analysis"])
            scenario["cv_cited"] = sum(cites_cv(turn["question"], terms) for turn in scenario["turns"])
    write_report(data["pytest"], data["scenarios"], data["judgement"])
    print(f"Rapport recalculé dans {REPORT_FILE}")


if __name__ == "__main__":
    # python -m tests.manual_scenarios --rebuild : recalcule le rapport sans appeler le LLM
    rebuild() if "--rebuild" in sys.argv else main()
