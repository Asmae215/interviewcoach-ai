"""Interface Streamlit : connexion, entraînement (CV → analyse → entretien → avis), tableau de bord."""

import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st

from errors import format_validation_errors
from texts import CRITERIA_COLORS, DIFFICULTIES, INTERVIEW_TYPES, LEVELS, TEXTS

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


# --- Déploiement sur Streamlit Community Cloud (étape 10) ---

def load_cloud_secrets() -> None:
    """Recopie les secrets de Streamlit Cloud dans les variables d'environnement lues par le backend."""
    try:
        for key, value in st.secrets.items():
            if isinstance(value, (str, int, float, bool)):
                os.environ.setdefault(key, str(value))
    except Exception:  # en local, pas de fichier .streamlit/secrets.toml : on utilise .env
        pass


@st.cache_resource
def start_embedded_api() -> bool:
    """Streamlit Cloud n'exécute qu'un processus : l'API FastAPI y démarre en arrière-plan.

    Elle écoute seulement 127.0.0.1 (jamais exposée sur internet). Lancée une seule fois
    par serveur grâce à st.cache_resource, même si plusieurs candidats se connectent.
    """
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)  # pour « import backend » depuis frontend/app.py
    import uvicorn

    from backend.main import app as api

    server = uvicorn.Server(uvicorn.Config(api, host="127.0.0.1", port=8000, log_level="warning"))
    threading.Thread(target=server.run, daemon=True, name="api").start()
    for _ in range(40):  # au plus 20 s pour démarrer
        try:
            if requests.get(f"{API_URL}/health", timeout=1).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


load_cloud_secrets()
if os.getenv("EMBEDDED_API") == "1":
    start_embedded_api()


# --- Appels au backend ---

def reset_session() -> None:
    """Oublie tout (jeton, CV, entretien…) sauf la langue choisie."""
    for key in list(st.session_state.keys()):
        if key != "language":
            del st.session_state[key]


def call_api(method: str, path: str, t: dict, **kwargs) -> requests.Response | None:
    """Appelle le backend avec le jeton de connexion ; message clair s'il ne répond pas."""
    kwargs.setdefault("timeout", 30)
    token = st.session_state.get("token")
    if token:
        kwargs.setdefault("headers", {})["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, f"{API_URL}{path}", **kwargs)
    except requests.RequestException:
        st.error(t["api_down"])
        return None
    if response.status_code == 401 and token:  # session expirée : retour à la connexion
        reset_session()
        st.session_state.expired = True
        st.rerun()
    return response


def show_error(response: requests.Response) -> None:
    """Affiche le message d'erreur renvoyé par l'API."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = response.text
    if isinstance(detail, dict):
        detail = detail.get("message", detail)
    elif isinstance(detail, list):  # erreurs de validation Pydantic, traduites
        detail = format_validation_errors(detail, st.session_state.get("language", "fr"))
    st.error(str(detail))


def format_date(value: str, language: str) -> str:
    moment = datetime.fromisoformat(value)
    return moment.strftime("%d/%m/%Y %H:%M" if language == "fr" else "%Y-%m-%d %H:%M")


# --- Affichages réutilisés ---

def show_analysis(analysis: dict, t: dict) -> None:
    """Affiche l'analyse structurée du CV."""
    st.markdown(f"**{t['summary']}** : {analysis['summary']}")
    st.markdown(f"**{t['skills']}** : " + ", ".join(analysis["skills"]))
    st.markdown(f"**{t['experiences']}**")
    for exp in analysis["experiences"]:
        st.markdown(f"- {exp['title']} — {exp['organization']} {exp['period']}")
    st.markdown(f"**{t['education']}**")
    for edu in analysis["education"]:
        st.markdown(f"- {edu['degree']} — {edu['school']} {edu['year']}")
    if analysis["projects"]:
        st.markdown(f"**{t['projects']}**")
        for project in analysis["projects"]:
            st.markdown(f"- {project['name']} : {project['description']}")
    st.markdown(f"**{t['weaknesses']}**")
    for weakness in analysis["weaknesses"]:
        st.markdown(f"- {weakness}")


def show_report(report: dict, t: dict) -> None:
    """Affiche l'avis du recruteur : notes justifiées, conseils, reformulation."""
    st.warning(report["disclaimer"])

    columns = st.columns(5)
    columns[0].metric(t["average"], f"{report['average']}/5")
    for column, (key, label) in zip(columns[1:], t["criteria"].items()):
        column.metric(label, f"{report['scores'][key]['score']}/5")
    for key, label in t["criteria"].items():
        st.markdown(f"**{label}** : {report['scores'][key]['justification']}")

    st.subheader(t["strengths"])
    for item in report["strengths"]:
        st.markdown(f"- {item}")
    st.subheader(t["improvements"])
    for item in report["improvements"]:
        st.markdown(f"- {item}")

    weakest = report["weakest_answer"]
    st.subheader(t["weakest"])
    st.markdown(f"**{t['question']}** : {weakest['question']}")
    st.markdown(f"**{t['answer']}** : {weakest['answer']}")
    st.markdown(f"**{t['why']}** : {weakest['why']}")
    st.info(f"**{t['improved']}** : {weakest['improved_answer']}")

    st.subheader(t["overall"])
    st.write(report["overall_feedback"])


def show_messages(messages: list[dict]) -> None:
    for message in messages:
        with st.chat_message("assistant" if message["role"] == "recruiter" else "user"):
            st.write(message["content"])


# --- Page de connexion ---

def start_session(data: dict, t: dict) -> None:
    """Garde le jeton, puis recharge le dernier CV du candidat."""
    st.session_state.token = data["token"]
    st.session_state.candidate = data["candidate"]
    # Appliquée au prochain affichage (un widget ne peut pas changer après sa création)
    st.session_state.pending_language = data["candidate"]["language"]
    response = call_api("GET", f"/candidates/{data['candidate']['id']}/cvs", t)
    if response is not None and response.status_code == 200 and response.json():
        st.session_state.cv = response.json()[0]
    st.rerun()


def page_login(t: dict, language: str) -> None:
    if st.session_state.pop("expired", False):
        st.warning(t["session_expired"])
    login_tab, register_tab = st.tabs([t["login_tab"], t["register_tab"]])

    with login_tab:
        with st.form("login"):
            username = st.text_input(t["username"])
            password = st.text_input(t["password"], type="password")
            if st.form_submit_button(t["login"]):
                payload = {"username": username, "password": password, "language": language}
                response = call_api("POST", "/auth/login", t, json=payload)
                if response is not None and response.status_code == 200:
                    start_session(response.json(), t)
                elif response is not None:
                    show_error(response)

    with register_tab:
        with st.form("register"):
            name = st.text_input(t["name"])
            username = st.text_input(t["username"], key="register_username")
            password = st.text_input(t["password"], type="password", key="register_password")
            job = st.text_input(t["job"])
            level = st.selectbox(t["level"], list(LEVELS[language]), format_func=LEVELS[language].get)
            if st.form_submit_button(t["register"]):
                payload = {
                    "name": name, "username": username, "password": password,
                    "target_job": job, "level": level, "language": language,
                }
                response = call_api("POST", "/auth/register", t, json=payload)
                if response is not None and response.status_code == 201:
                    start_session(response.json(), t)
                elif response is not None:
                    show_error(response)


# --- Page « S'entraîner » : CV → analyse → entretien → avis ---

def section_cv(t: dict) -> None:
    candidate = st.session_state.candidate
    st.header(t["cv"])
    uploaded = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded is not None and st.button(t["send"]):
        files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
        response = call_api("POST", f"/candidates/{candidate['id']}/cv", t, files=files)
        if response is not None and response.status_code == 201:
            st.session_state.cv = response.json()
        elif response is not None:
            show_error(response)

    if "cv" not in st.session_state:
        return

    st.header(t["check"])
    cv = st.session_state.cv
    text = st.text_area("CV", cv["extracted_text"], height=400, label_visibility="collapsed")
    if st.button(t["save"]):
        response = call_api("PUT", f"/cvs/{cv['id']}/text", t, json={"text": text})
        if response is not None and response.status_code == 200:
            st.session_state.cv = response.json()
            st.success(t["saved"])
        elif response is not None:
            show_error(response)

    # Consentement puis analyse du CV par le LLM
    st.header(t["analysis"])
    cv = st.session_state.cv
    st.info(t["consent_info"])
    consent = st.checkbox(t["consent"])
    if st.button(t["analyze"], disabled=not consent):
        with st.spinner(t["analyzing"]):
            response = call_api(
                "POST", f"/cvs/{cv['id']}/analyze", t, json={"consent": consent}, timeout=120
            )
        if response is not None and response.status_code == 200:
            st.session_state.cv = response.json()
            cv = st.session_state.cv
        elif response is not None:
            show_error(response)
    if cv.get("analysis"):
        show_analysis(cv["analysis"], t)


def section_report(interview: dict, t: dict) -> None:
    """Avis du recruteur : demandé automatiquement une fois, puis bouton « Réessayer »."""
    st.header(t["report"])
    report = st.session_state.get("report")
    if report is not None:
        show_report(report, t)
        return
    auto = not st.session_state.get("report_attempted")
    if auto or st.button(t["retry"]):
        st.session_state.report_attempted = True
        with st.spinner(t["evaluating"]):
            response = call_api("POST", f"/interviews/{interview['id']}/report", t, timeout=180)
        if response is not None and response.status_code == 200:
            st.session_state.report = response.json()
            st.rerun()
        elif response is not None:
            show_error(response)
        if auto:
            st.button(t["retry"])  # relance manuelle après un échec


def section_interview(t: dict, language: str) -> None:
    """Entretien : une question à la fois (le backend refuse aussi sans CV analysé)."""
    if not st.session_state.get("cv", {}).get("analysis"):
        return
    st.header(t["interview"])

    if "interview" not in st.session_state:
        interview_type = st.selectbox(
            t["type"], list(INTERVIEW_TYPES[language]), format_func=INTERVIEW_TYPES[language].get
        )
        difficulty = st.selectbox(
            t["difficulty"], list(DIFFICULTIES[language]), index=1,
            format_func=DIFFICULTIES[language].get,
        )
        if st.button(t["start"]):
            with st.spinner(t["starting"]):
                response = call_api(
                    "POST", f"/candidates/{st.session_state.candidate['id']}/interviews", t,
                    json={"interview_type": interview_type, "difficulty": difficulty}, timeout=120,
                )
            if response is not None and response.status_code == 201:
                st.session_state.interview = response.json()
                st.rerun()
            elif response is not None:
                show_error(response)
        return

    interview = st.session_state.interview
    st.progress(
        interview["question_number"] / interview["total_questions"],
        text=t["progress"].format(n=interview["question_number"], total=interview["total_questions"]),
    )
    show_messages(interview["messages"])

    if interview["status"] == "en_cours":
        answer = st.chat_input(t["your_answer"])
        if answer:
            with st.spinner(t["thinking"]):
                response = call_api(
                    "POST", f"/interviews/{interview['id']}/answers", t,
                    json={"answer": answer}, timeout=120,
                )
            if response is not None and response.status_code == 200:
                st.session_state.interview = response.json()
                st.rerun()
            elif response is not None:
                show_error(response)
                st.caption(t["not_sent"])
                st.code(answer, language=None)
        return

    st.success(t["finished"])
    section_report(interview, t)
    if st.button(t["new_interview"]):
        for key in ("interview", "report", "report_attempted"):
            st.session_state.pop(key, None)
        st.rerun()


def page_practice(t: dict, language: str) -> None:
    candidate = st.session_state.candidate
    st.header(t["profile"])
    st.success(
        f"{candidate['name']} — {candidate['target_job']} — "
        f"{LEVELS[language].get(candidate['level'], candidate['level'])}"
    )
    section_cv(t)
    section_interview(t, language)


# --- Page « Tableau de bord » ---

def progress_charts(rows: list[tuple[int, dict]], t: dict, language: str) -> None:
    """Un petit graphique par critère (même échelle 0-5), pour éviter les courbes superposées."""
    data = pd.DataFrame(
        [{"session": number, "date": format_date(row["created_at"], language), **row["scores"]}
         for number, row in rows]
    )
    columns = st.columns(2)
    for index, ((key, label), color) in enumerate(zip(t["criteria"].items(), CRITERIA_COLORS)):
        chart = (
            alt.Chart(data, title=label, height=200)
            .mark_line(strokeWidth=2, color=color, point=alt.OverlayMarkDef(size=80, filled=True, color=color))
            .encode(
                x=alt.X("session:O", title=t["session"], axis=alt.Axis(labelAngle=0)),
                y=alt.Y(f"{key}:Q", title=t["score_axis"], scale=alt.Scale(domain=[0, 5]),
                        axis=alt.Axis(values=[1, 2, 3, 4, 5])),
                tooltip=[
                    alt.Tooltip("session:O", title=t["session"]),
                    alt.Tooltip("date:N", title=t["date"]),
                    alt.Tooltip(f"{key}:Q", title=label),
                ],
            )
        )
        columns[index % 2].altair_chart(chart, width="stretch")


def interview_detail(row: dict, t: dict) -> None:
    """Rapport (ou conversation) d'un entretien passé, et sa suppression."""
    interview_id = row["id"]
    if row["scores"]:
        response = call_api("GET", f"/interviews/{interview_id}/report", t)
        if response is not None and response.status_code == 200:
            show_report(response.json(), t)
    elif row["status"] == "terminee":
        st.info(t["no_report"])
        if st.button(t["retry"], key=f"report_{interview_id}"):
            with st.spinner(t["evaluating"]):
                response = call_api("POST", f"/interviews/{interview_id}/report", t, timeout=180)
            if response is not None and response.status_code == 200:
                st.rerun()
            elif response is not None:
                show_error(response)

    with st.expander(t["conversation"]):
        response = call_api("GET", f"/interviews/{interview_id}", t)
        if response is not None and response.status_code == 200:
            show_messages(response.json()["messages"])

    confirm = st.checkbox(t["confirm_delete"], key=f"confirm_interview_{interview_id}")
    if st.button(t["delete_interview"], disabled=not confirm, key=f"delete_interview_{interview_id}"):
        response = call_api("DELETE", f"/interviews/{interview_id}", t)
        if response is not None and response.status_code == 204:
            if st.session_state.get("interview", {}).get("id") == interview_id:
                for key in ("interview", "report", "report_attempted"):
                    st.session_state.pop(key, None)
            st.success(t["deleted"])
            st.rerun()


def section_cvs(t: dict, language: str) -> None:
    st.subheader(t["my_cvs"])
    candidate = st.session_state.candidate
    response = call_api("GET", f"/candidates/{candidate['id']}/cvs", t)
    if response is None or response.status_code != 200:
        return
    cvs = response.json()
    if not cvs:
        st.caption(t["no_cv"])
    for number, cv in enumerate(reversed(cvs), start=1):
        state = t["analyzed"] if cv["analysis"] else t["not_analyzed"]
        st.markdown(t["cv_item"].format(n=number, date=format_date(cv["created_at"], language), state=state))
        confirm = st.checkbox(t["confirm_delete"], key=f"confirm_cv_{cv['id']}")
        if st.button(t["delete_cv"], disabled=not confirm, key=f"delete_cv_{cv['id']}"):
            delete = call_api("DELETE", f"/cvs/{cv['id']}", t)
            if delete is not None and delete.status_code == 204:
                if st.session_state.get("cv", {}).get("id") == cv["id"]:
                    st.session_state.pop("cv", None)
                st.success(t["deleted"])
                st.rerun()


def page_dashboard(t: dict, language: str) -> None:
    st.header(t["dashboard"])
    candidate = st.session_state.candidate
    response = call_api("GET", f"/candidates/{candidate['id']}/interviews", t)
    if response is None:
        return
    if response.status_code != 200:
        show_error(response)
        return

    rows = list(enumerate(response.json(), start=1))  # (numéro d'entretien, ligne)
    if not rows:
        st.info(t["no_interviews"])
    else:
        st.subheader(t["progression"])
        scored = [(number, row) for number, row in rows if row["scores"]]
        if scored:
            progress_charts(scored, t, language)
        else:
            st.info(t["need_report"])

        # Tableau : la même information que les graphiques, lisible sans les couleurs
        st.subheader(t["history"])
        table = pd.DataFrame([
            {
                "#": number,
                t["date"]: format_date(row["created_at"], language),
                t["type"]: INTERVIEW_TYPES[language].get(row["interview_type"], row["interview_type"]),
                t["difficulty"]: DIFFICULTIES[language].get(row["difficulty"], row["difficulty"]),
                t["status"]: t["statuses"].get(row["status"], row["status"]),
                t["average"]: row["average"],
                **{label: (row["scores"] or {}).get(key) for key, label in t["criteria"].items()},
            }
            for number, row in rows
        ])
        st.dataframe(table, hide_index=True, width="stretch")

        labels = {
            row["id"]: f"{t['session']} {number} — {format_date(row['created_at'], language)} — "
            f"{INTERVIEW_TYPES[language].get(row['interview_type'], row['interview_type'])}"
            + (f" — {row['average']}/5" if row["average"] is not None else "")
            for number, row in rows
        }
        by_id = {row["id"]: row for _, row in rows}
        selected = st.selectbox(t["open"], list(reversed(list(by_id))), format_func=labels.get)
        interview_detail(by_id[selected], t)

    section_cvs(t, language)


# --- Mise en page générale ---

if "pending_language" in st.session_state:  # langue du profil, après connexion
    st.session_state.language = st.session_state.pop("pending_language")
st.session_state.setdefault("language", "fr")
language = st.sidebar.radio("Langue / Language", ["fr", "en"], format_func=str.upper, key="language")
t = TEXTS[language]
st.title(t["title"])

if "token" not in st.session_state:
    page_login(t, language)
else:
    candidate = st.session_state.candidate
    # Changer la langue dans la barre latérale met aussi à jour le profil (backend)
    if candidate["language"] != language:
        response = call_api("PATCH", f"/candidates/{candidate['id']}", t, json={"language": language})
        if response is not None and response.status_code == 200:
            st.session_state.candidate = response.json()

    st.sidebar.caption(t["logged_as"].format(name=st.session_state.candidate["name"]))
    page = st.sidebar.radio(
        t["nav"], ["practice", "dashboard"],
        format_func=lambda key: t["nav_practice"] if key == "practice" else t["nav_dashboard"],
    )
    if st.sidebar.button(t["logout"]):
        call_api("POST", "/auth/logout", t)
        reset_session()
        st.rerun()

    if page == "practice":
        page_practice(t, language)
    else:
        page_dashboard(t, language)
