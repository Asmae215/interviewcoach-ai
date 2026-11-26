# InterviewCoach AI — un seul conteneur : FastAPI (interne) + Streamlit (public)
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances d'abord : cette couche reste en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY prompts/ prompts/
COPY data/askedbefore_cs_interview_questions.csv data/
COPY start.sh .

# Utilisateur sans droits d'administration ; data/uploads est un dossier temporaire
RUN mkdir -p data/uploads \
    && useradd --create-home appuser \
    && chown -R appuser /app \
    && chmod +x start.sh
USER appuser

# Render fournit le port public dans $PORT (8501 en local)
ENV PORT=8501
EXPOSE 8501

CMD ["./start.sh"]
