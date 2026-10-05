"""Edge-case tests for app.scoring.score_candidate."""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scoring import score_candidate  # noqa: E402


def _candidate(**overrides) -> dict:
    base = {
        "id": "cand_1",
        "job_id": "job_1",
        "name": "Test Candidate",
        "email": "test@example.com",
        "skills": [],
        "experience_years": 0.0,
        "raw_text": "",
        "matches": [],
        "score": 0.0,
    }
    base.update(overrides)
    return base


def test_must_have_verified_when_evidence_supports_it():
    """A must-have requirement with clear, matching resume evidence scores full marks."""

    requirements = [
        {"id": "req_1", "text": "At least 5 years of Python experience", "type": "must"},
    ]
    candidate = _candidate(
        skills=["Python"],
        experience_years=6.0,
        raw_text="Senior engineer with 6 years of professional Python experience.",
    )

    result = score_candidate(candidate, requirements)

    assert result["score"] == 1.0
    assert len(result["matches"]) == 1
    match = result["matches"][0]
    assert match["requirement_id"] == "req_1"
    assert match["status"] == "verified"
    assert match["evidence"][0]["status"] == "verified"
    assert match["evidence"][0]["confidence"] > 0


def test_must_have_missing_when_no_evidence_exists():
    """A must-have requirement with nothing in the resume supporting it earns zero score."""

    requirements = [
        {"id": "req_1", "text": "Experience with Kubernetes", "type": "must"},
    ]
    candidate = _candidate(
        skills=["HTML", "CSS"],
        experience_years=0.0,
        raw_text="Recent graduate with no professional experience yet.",
    )

    result = score_candidate(candidate, requirements)

    assert result["score"] == 0.0
    match = result["matches"][0]
    assert match["requirement_id"] == "req_1"
    assert match["status"] == "missing"
    assert match["evidence"][0]["confidence"] == 0.0


def test_missing_must_have_outweighs_verified_nice_to_have():
    """A verified nice-to-have cannot compensate for a missing must-have in the score."""

    requirements = [
        {"id": "req_must", "text": "Experience with Kubernetes", "type": "must"},
        {"id": "req_nice", "text": "Docker", "type": "nice"},
    ]
    candidate = _candidate(
        skills=["Docker"],
        experience_years=3.0,
        raw_text="Built and deployed services using Docker containers for 3 years.",
    )

    result = score_candidate(candidate, requirements)

    statuses = {match["requirement_id"]: match["status"] for match in result["matches"]}
    assert statuses["req_must"] == "missing"
    assert statuses["req_nice"] == "verified"
    # must-have is worth 2 points, nice-to-have 1 point; only the nice-to-have
    # point was earned, so the score must stay well below a passing ranking.
    assert result["score"] == pytest.approx(1 / 3, abs=1e-4)


def test_contradicted_evidence_does_not_count_as_verified():
    """Explicit negation in the resume text is scored as contradicted, not verified."""

    requirements = [
        {"id": "req_1", "text": "Experience with Kubernetes", "type": "must"},
    ]
    candidate = _candidate(
        skills=[],
        experience_years=4.0,
        raw_text="No experience with Kubernetes or container orchestration.",
    )

    result = score_candidate(candidate, requirements)

    match = result["matches"][0]
    assert match["status"] == "contradicted"
    assert result["score"] == 0.0


def test_existing_recruiter_decision_is_preserved_across_rescoring():
    """A prior human-set evidence status survives recalculation (e.g. after a fact edit)."""

    requirements = [
        {"id": "req_1", "text": "Experience with Kubernetes", "type": "must"},
    ]
    candidate = _candidate(
        skills=[],
        experience_years=0.0,
        raw_text="No mention of Kubernetes anywhere.",
        matches=[
            {
                "requirement_id": "req_1",
                "evidence": [
                    {"snippet": "Recruiter confirmed via reference call.", "confidence": 1.0, "status": "verified"}
                ],
                "status": "verified",
            }
        ],
    )

    result = score_candidate(candidate, requirements)

    match = result["matches"][0]
    assert match["status"] == "verified"
    assert result["score"] == 1.0
