import os

import requests
from dotenv import load_dotenv

load_dotenv()
reponse = requests.get(
    "https://generativelanguage.googleapis.com/v1beta/models",
    headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY")},
    params={"pageSize": 100},
    timeout=30,
)
for modele in reponse.json().get("models", []):
    if "generateContent" in modele.get("supportedGenerationMethods", []):
        print(modele["name"].replace("models/", ""))
