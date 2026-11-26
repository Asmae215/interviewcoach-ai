"""Interface Streamlit — étape 4 : profil candidat, dépôt du CV et correction du texte."""

import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

TEXTS = {
    "fr": {
        "title": "InterviewCoach AI",
        "profile": "1. Ton profil",
        "name": "Nom",
        "job": "Poste visé",
        "level": "Niveau",
        "create": "Créer mon profil",
        "created": "Profil créé.",
        "cv": "2. Ton CV (PDF, 5 Mo max)",
        "send": "Envoyer le CV",
        "check": "3. Vérifie le texte extrait et corrige-le si besoin",
        "save": "Enregistrer les corrections",
        "saved": "Texte enregistré.",
        "api_down": "Le serveur ne répond pas. Lance d'abord le backend (uvicorn).",
    },
    "en": {
        "title": "InterviewCoach AI",
        "profile": "1. Your profile",
        "name": "Name",
        "job": "Target job",
        "level": "Level",
        "create": "Create my profile",
        "created": "Profile created.",
        "cv": "2. Your CV (PDF, 5 MB max)",
        "send": "Upload CV",
        "check": "3. Check the extracted text and fix it if needed",
        "save": "Save corrections",
        "saved": "Text saved.",
        "api_down": "The server is not responding. Start the backend (uvicorn) first.",
    },
}
LEVELS = {
    "fr": {"etudiant": "Étudiant", "junior": "Junior", "confirme": "Confirmé"},
    "en": {"etudiant": "Student", "junior": "Junior", "confirme": "Experienced"},
}


def call_api(method: str, path: str, t: dict, **kwargs) -> requests.Response | None:
    """Appelle le backend ; affiche un message clair s'il ne répond pas."""
    try:
        return requests.request(method, f"{API_URL}{path}", timeout=30, **kwargs)
    except requests.RequestException:
        st.error(t["api_down"])
        return None


def show_error(response: requests.Response) -> None:
    """Affiche le message d'erreur renvoyé par l'API."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = response.text
    if isinstance(detail, dict):
        detail = detail.get("message", detail)
    elif isinstance(detail, list):  # erreurs de validation Pydantic
        detail = " ; ".join(err.get("msg", str(err)) for err in detail)
    st.error(str(detail))


language = st.sidebar.radio("Langue / Language", ["fr", "en"], format_func=str.upper)
t = TEXTS[language]
st.title(t["title"])

# 1. Profil
st.header(t["profile"])
if "candidate" not in st.session_state:
    with st.form("profile"):
        name = st.text_input(t["name"])
        job = st.text_input(t["job"])
        level = st.selectbox(t["level"], list(LEVELS[language]), format_func=LEVELS[language].get)
        if st.form_submit_button(t["create"]):
            payload = {"name": name, "target_job": job, "level": level, "language": language}
            response = call_api("POST", "/candidates", t, json=payload)
            if response is not None and response.status_code == 201:
                st.session_state.candidate = response.json()
                st.rerun()
            elif response is not None:
                show_error(response)
else:
    candidate = st.session_state.candidate
    st.success(f"{candidate['name']} — {candidate['target_job']}")

# 2. Dépôt du CV
if "candidate" in st.session_state:
    st.header(t["cv"])
    uploaded = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded is not None and st.button(t["send"]):
        files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
        path = f"/candidates/{st.session_state.candidate['id']}/cv"
        response = call_api("POST", path, t, files=files)
        if response is not None and response.status_code == 201:
            st.session_state.cv = response.json()
        elif response is not None:
            show_error(response)

# 3. Vérification et correction du texte extrait
if "cv" in st.session_state:
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
