"""Job intake and candidate querying routes.

Per docs/CONTRACT.md:
- POST /api/jobs body:{description:str} -> {job_id:str, requirements:[Requirement]}
- GET /api/jobs/{job_id}/candidates -> {candidates:[Candidate]} sorted by score desc
"""

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.models import Job, Requirement
from app.requirements import extract_requirements

router = APIRouter(tags=["jobs"])


class JobCreateRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Raw job description text")


class JobResponse(BaseModel):
    job_id: str
    requirements: List[Requirement]


@router.post("/api/jobs", response_model=JobResponse)
async def create_job(payload: JobCreateRequest):
    """Intake a job description, extract must/nice requirements, and persist to database."""
    db.init_db()

    description = payload.description.strip()
    if not description:
        raise HTTPException(status_code=400, detail="Job description cannot be empty")

    requirements = extract_requirements(description)
    job_id = f"job_{uuid.uuid4().hex[:8]}"

    job = Job(
        id=job_id,
        description=description,
        requirements=requirements,
    )

    db.save_job(job)

    return JobResponse(
        job_id=job.id,
        requirements=job.requirements,
    )


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Retrieve job details and extracted requirements by job_id."""
    db.init_db()
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/api/jobs/{job_id}/candidates")
async def get_job_candidates(job_id: str):
    """Retrieve all candidates for a job_id sorted by score desc."""
    db.init_db()
    candidates = db.list_candidates(job_id)
    return {"candidates": candidates}
