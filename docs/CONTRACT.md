# Evidence-First Resume Triage - API Contract

Base URL: http://localhost:8000 (env PORT=8000, DB_PATH=backend/app.db)
All responses are JSON. Backend: FastAPI + SQLite. Frontend: static files served at `/` by the same app.

## Data shapes
Requirement: {id:str, text:str, type:"must"|"nice"}
Evidence: {snippet:str, confidence:float(0-1), status:"verified"|"uncertain"|"contradicted"|"missing"}
RequirementMatch: {requirement_id:str, evidence:[Evidence], status:"verified"|"uncertain"|"contradicted"|"missing"}
Candidate: {id:str, job_id:str, name:str, email:str, skills:[str], experience_years:float, raw_text:str, matches:[RequirementMatch], score:float}

## Endpoints
POST /api/jobs body:{description:str} -> {job_id:str, requirements:[Requirement]}
POST /api/candidates/upload multipart: job_id:str, files:[file] -> {candidates:[Candidate]} (.pdf/.docx/.txt)
GET /api/jobs/{job_id}/candidates -> {candidates:[Candidate]} sorted by score desc
PATCH /api/candidates/{id}/facts body:{field:str, value:any} -> {candidate:Candidate} (recalculates score)
POST /api/candidates/{id}/evidence/{requirement_id}/status body:{status:"verified"|"uncertain"|"contradicted"|"missing"} -> {candidate:Candidate}
GET /api/jobs/{job_id}/export -> {markdown:str} (evidence-backed shortlist report)

## Shared function signature (backend/app/scoring.py)
def score_candidate(candidate: dict, requirements: list[dict]) -> dict
  # fills candidate["matches"] and candidate["score"], using only evidence with status "verified" for the score

## Env vars
PORT=8000, DB_PATH=backend/app.db

## Run
cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000
Frontend: frontend/index.html (job + upload) and frontend/dashboard.html (ranking + evidence queue), mounted as static files by app/main.py.
