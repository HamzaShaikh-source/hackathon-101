"""Pydantic data models shared across the backend, matching docs/CONTRACT.md."""

from typing import Literal

from pydantic import BaseModel, Field

EvidenceStatus = Literal["verified", "uncertain", "contradicted", "missing"]
RequirementType = Literal["must", "nice"]


class Requirement(BaseModel):
    id: str
    text: str
    type: RequirementType


class Evidence(BaseModel):
    snippet: str
    confidence: float = Field(ge=0, le=1)
    status: EvidenceStatus


class RequirementMatch(BaseModel):
    requirement_id: str
    evidence: list[Evidence] = Field(default_factory=list)
    status: EvidenceStatus


class Candidate(BaseModel):
    id: str
    job_id: str
    name: str
    email: str
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0
    raw_text: str
    matches: list[RequirementMatch] = Field(default_factory=list)
    score: float = 0


class Job(BaseModel):
    id: str
    description: str
    requirements: list[Requirement] = Field(default_factory=list)
