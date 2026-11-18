import time

from backend.services.llm import ask_llm, LLMError

QUESTIONS = [
    ("fr", "Tu es un recruteur. Pose-moi une question d'entretien pour un stage en data science."),
    ("en", "You are a recruiter. Ask me one interview question for a data science internship."),
]

for langue, question in QUESTIONS:
    debut = time.time()
    try:
        reponse = ask_llm(question)
    except LLMError as erreur:
        print("ERREUR :", erreur)
        break
    duree = time.time() - debut
    print(f"[{langue}] ({duree:.1f} s)\n{reponse}\n")
