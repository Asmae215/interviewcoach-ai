from fastapi import FastAPI

import backend.models  # noqa: F401
from backend.database import Base, engine
from backend.routers import candidates

Base.metadata.create_all(engine)

app = FastAPI(title="InterviewCoach AI")
app.include_router(candidates.router)


@app.get("/health")
def health():
    return {"status": "ok"}
