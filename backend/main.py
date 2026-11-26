from fastapi import FastAPI

import backend.models  # noqa: F401
from backend.database import Base, add_missing_columns, engine
from backend.routers import auth, candidates, cv, dashboard, interview, reports

Base.metadata.create_all(engine)
add_missing_columns()

app = FastAPI(title="InterviewCoach AI")
app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(cv.router)
app.include_router(interview.router)
app.include_router(reports.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
