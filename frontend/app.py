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
        "analysis": "4. Analyse de ton CV par l'IA",
        "consent_info": (
            "Ton CV va être envoyé à un service d'IA externe (Google Gemini ou Groq) "
            "pour être analysé. Il n'est pas utilisé pour entraîner un modèle."
        ),
        "consent": "J'accepte que mon CV soit analysé par une IA.",
        "analyze": "Analyser mon CV",
        "analyzing": "Analyse en cours…",
        "summary": "Résumé",
        "skills": "Compétences",
        "experiences": "Expériences",
        "education": "Formation",
        "projects": "Projets",
        "weaknesses": "Points à renforcer pour le poste",
        "interview": "5. Entretien avec le recruteur IA",
        "type": "Type d'entretien",
        "difficulty": "Difficulté",
        "start": "Commencer l'entretien",
        "starting": "Le recruteur prépare sa première question…",
        "thinking": "Le recruteur réfléchit…",
        "progress": "Question {n} sur {total}",
        "your_answer": "Ta réponse…",
        "not_sent": "Ta réponse n'a pas été envoyée, tu peux la copier et réessayer :",
        "finished": "Entretien terminé. L'avis du recruteur arrive à l'étape suivante.",
        "new_interview": "Nouvel entretien",
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
        "analysis": "4. AI analysis of your CV",
        "consent_info": (
            "Your CV will be sent to an external AI service (Google Gemini or Groq) "
            "to be analysed. It is not used to train a model."
        ),
        "consent": "I agree that my CV is analysed by an AI.",
        "analyze": "Analyse my CV",
        "analyzing": "Analysing…",
        "summary": "Summary",
        "skills": "Skills",
        "experiences": "Experience",
        "education": "Education",
        "projects": "Projects",
        "weaknesses": "Areas to strengthen for the job",
        "interview": "5. Interview with the AI recruiter",
        "type": "Interview type",
        "difficulty": "Difficulty",
        "start": "Start the interview",
        "starting": "The recruiter is preparing the first question…",
        "thinking": "The recruiter is thinking…",
        "progress": "Question {n} of {total}",
        "your_answer": "Your answer…",
        "not_sent": "Your answer was not sent, you can copy it and retry:",
        "finished": "Interview over. The recruiter's feedback comes in the next step.",
        "new_interview": "New interview",
    },
}
LEVELS = {
    "fr": {"etudiant": "Étudiant", "junior": "Junior", "confirme": "Confirmé"},
    "en": {"etudiant": "Student", "junior": "Junior", "confirme": "Experienced"},
}
INTERVIEW_TYPES = {
    "fr": {"rh": "RH", "technique": "Technique", "comportemental": "Comportemental", "mixte": "Mixte"},
    "en": {"rh": "HR", "technique": "Technical", "comportemental": "Behavioural", "mixte": "Mixed"},
}
DIFFICULTIES = {
    "fr": {"debutant": "Débutant", "intermediaire": "Intermédiaire", "avance": "Avancé"},
    "en": {"debutant": "Beginner", "intermediaire": "Intermediate", "avance": "Advanced"},
}


def call_api(method: str, path: str, t: dict, **kwargs) -> requests.Response | None:
    """Appelle le backend ; affiche un message clair s'il ne répond pas."""
    kwargs.setdefault("timeout", 30)
    try:
        return requests.request(method, f"{API_URL}{path}", **kwargs)
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

# 4. Consentement puis analyse du CV par le LLM
if "cv" in st.session_state:
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

# 5. Entretien : une question à la fois (le backend refuse aussi sans CV analysé)
if st.session_state.get("cv", {}).get("analysis"):
    st.header(t["interview"])

    if "interview" not in st.session_state:
        interview_type = st.selectbox(
            t["type"], list(INTERVIEW_TYPES[language]), format_func=INTERVIEW_TYPES[language].get
        )
        difficulty = st.selectbox(
            t["difficulty"], list(DIFFICULTIES[language]), index=1, format_func=DIFFICULTIES[language].get
        )
        if st.button(t["start"]):
            with st.spinner(t["starting"]):
                response = call_api(
                    "POST",
                    f"/candidates/{st.session_state.candidate['id']}/interviews",
                    t,
                    json={"interview_type": interview_type, "difficulty": difficulty},
                    timeout=120,
                )
            if response is not None and response.status_code == 201:
                st.session_state.interview = response.json()
                st.rerun()
            elif response is not None:
                show_error(response)
    else:
        interview = st.session_state.interview
        st.progress(
            interview["question_number"] / interview["total_questions"],
            text=t["progress"].format(n=interview["question_number"], total=interview["total_questions"]),
        )
        for message in interview["messages"]:
            role = "assistant" if message["role"] == "recruiter" else "user"
            with st.chat_message(role):
                st.write(message["content"])

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
        else:
            st.success(t["finished"])
            if st.button(t["new_interview"]):
                del st.session_state["interview"]
                st.rerun()
