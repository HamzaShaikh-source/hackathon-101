"""Candidate fact corrections and evidence decisions."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from . import db
from .scoring import score_candidate


router = APIRouter(prefix="/api/candidates", tags=["corrections"])

_EDITABLE_FACTS = {"name", "email", "skills", "experience_years"}
EvidenceStatus = Literal["verified", "uncertain", "contradicted", "missing"]


class FactCorrection(BaseModel):
    field: str
    value: Any

    @field_validator("field")
    @classmethod
    def valid_field(cls, value: str) -> str:
        if value not in _EDITABLE_FACTS:
            allowed = ", ".join(sorted(_EDITABLE_FACTS))
            raise ValueError(f"field must be one of: {allowed}")
        return value


class EvidenceCorrection(BaseModel):
    status: EvidenceStatus


def _candidate_or_404(candidate_id: str) -> dict:
    candidate = db.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


def _requirements_or_404(candidate: dict) -> list[dict]:
    job = db.get_job(candidate["job_id"])
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.get("requirements", [])


def _coerce_fact(field: str, value: Any) -> Any:
    if field in {"name", "email"}:
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(status_code=422, detail=f"{field} must be a non-empty string")
        return value.strip()
    if field == "skills":
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",") if item.strip()]
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise HTTPException(status_code=422, detail="skills must be a list of non-empty strings")
        return [item.strip() for item in value]
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="experience_years must be a number") from exc
    if number < 0:
        raise HTTPException(status_code=422, detail="experience_years cannot be negative")
    return number


def _save_scored(candidate: dict, requirements: list[dict]) -> dict:
    score_candidate(candidate, requirements)
    return db.save_candidate(candidate)


@router.patch("/{candidate_id}/facts")
def update_candidate_fact(candidate_id: str, correction: FactCorrection) -> dict:
    """Apply an editable candidate fact and recalculate the full evidence rubric."""

    candidate = _candidate_or_404(candidate_id)
    requirements = _requirements_or_404(candidate)
    candidate[correction.field] = _coerce_fact(correction.field, correction.value)
    # Match evidence is derived from candidate facts.  Clear it before
    # rescoring so a corrected fact cannot retain a stale automatic decision.
    candidate["matches"] = []
    return {"candidate": _save_scored(candidate, requirements)}


@router.post("/{candidate_id}/evidence/{requirement_id}/status")
def update_evidence_status(
    candidate_id: str,
    requirement_id: str,
    correction: EvidenceCorrection,
) -> dict:
    """Accept or reject one requirement's evidence, then recalculate its score."""

    candidate = _candidate_or_404(candidate_id)
    requirements = _requirements_or_404(candidate)
    if not any(str(requirement.get("id")) == requirement_id for requirement in requirements):
        raise HTTPException(status_code=404, detail="Requirement not found")

    # A stored candidate normally already has matches, but generating them here
    # keeps the endpoint correct for legacy rows or partially populated data.
    score_candidate(candidate, requirements)
    match = next(match for match in candidate["matches"] if match["requirement_id"] == requirement_id)
    evidence = match.get("evidence") or [{"snippet": "Recruiter decision", "confidence": 1.0}]
    for item in evidence:
        item["status"] = correction.status
    match["evidence"] = evidence
    match["status"] = correction.status
    return {"candidate": _save_scored(candidate, requirements)}
