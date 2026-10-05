"""Upload routes for candidate resumes.

Implements POST /api/candidates/upload and GET /api/jobs/{job_id}/candidates per docs/CONTRACT.md.
"""

import uuid
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import db
from app.models import Candidate
from app.parsing import parse_resume

try:
    from app.scoring import score_candidate
except ImportError:
    score_candidate = None

router = APIRouter(tags=["candidates"])


@router.post("/api/candidates/upload")
async def upload_candidates(
    job_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """Upload multipart resume files (.pdf, .docx, .txt), extract facts, and store in DB."""
    # Ensure database tables exist
    db.init_db()

    job = db.get_job(job_id)
    requirements = job.get("requirements", []) if job else []

    saved_candidates = []

    for file in files:
        file_bytes = await file.read()
        filename = file.filename or "resume.txt"

        # Parse candidate facts from raw file
        try:
            facts = parse_resume(file_bytes, filename)
        except Exception as e:
            # Fallback to empty facts if file parsing hits an error
            facts = {
                "name": "Unknown Candidate",
                "email": "",
                "skills": [],
                "experience_years": 0.0,
                "raw_text": f"Error parsing {filename}: {str(e)}",
            }

        candidate_id = f"cand_{uuid.uuid4().hex[:8]}"

        candidate_dict = {
            "id": candidate_id,
            "job_id": job_id,
            "name": facts.get("name") or "Unknown Candidate",
            "email": facts.get("email") or "",
            "skills": facts.get("skills") or [],
            "experience_years": float(facts.get("experience_years") or 0.0),
            "raw_text": facts.get("raw_text") or "",
            "matches": [],
            "score": 0.0,
        }

        # If scoring engine is available and requirements are defined, score candidate
        if score_candidate and requirements:
            try:
                candidate_dict = score_candidate(candidate_dict, requirements)
            except Exception:
                pass

        # Validate with Pydantic model
        validated = Candidate(**candidate_dict)

        # Store in SQLite
        saved = db.save_candidate(validated)
        saved_candidates.append(saved)

    return {"candidates": saved_candidates}


@router.get("/api/jobs/{job_id}/candidates")
async def get_job_candidates(job_id: str):
    """Retrieve all candidates associated with a job_id, ordered by score desc."""
    db.init_db()
    candidates = db.list_candidates(job_id)
    return {"candidates": candidates}
