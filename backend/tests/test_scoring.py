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


def test_score_changes_on_evidence_status_accept_and_reject():
    """Score increases when evidence is accepted as verified and decreases when rejected."""

    requirements = [
        {"id": "req_must", "text": "Python experience", "type": "must"},
        {"id": "req_nice", "text": "Kubernetes experience", "type": "nice"},
    ]
    # Initially candidate has no relevant skills or text
    cand = _candidate(
        skills=[],
        experience_years=0.0,
        raw_text="Generalist with no tech skills.",
    )

    # 1. Baseline: neither requirement is satisfied -> score 0.0
    initial = score_candidate(dict(cand), requirements)
    assert initial["score"] == 0.0

    # 2. Accept must-have requirement: status becomes "verified"
    cand_accept_must = dict(initial)
    cand_accept_must["matches"] = [
        {
            "requirement_id": "req_must",
            "evidence": [{"snippet": "Recruiter approved Python fact", "confidence": 1.0, "status": "verified"}],
            "status": "verified",
        }
    ]
    scored_must = score_candidate(cand_accept_must, requirements)
    assert scored_must["score"] > initial["score"]
    # must weight 2, nice weight 1 -> 2/3
    assert scored_must["score"] == pytest.approx(2 / 3, abs=1e-4)

    # 3. Accept nice-to-have as well: status becomes "verified"
    cand_accept_both = dict(scored_must)
    cand_accept_both["matches"] = [
        {
            "requirement_id": "req_must",
            "evidence": [{"snippet": "Recruiter approved Python fact", "confidence": 1.0, "status": "verified"}],
            "status": "verified",
        },
        {
            "requirement_id": "req_nice",
            "evidence": [{"snippet": "Recruiter approved Kubernetes certificate", "confidence": 1.0, "status": "verified"}],
            "status": "verified",
        },
    ]
    scored_both = score_candidate(cand_accept_both, requirements)
    assert scored_both["score"] > scored_must["score"]
    assert scored_both["score"] == 1.0

    # 4. Reject must-have: recruiter marks it "contradicted" -> score decreases
    cand_reject_must = dict(scored_both)
    cand_reject_must["matches"] = [
        {
            "requirement_id": "req_must",
            "evidence": [{"snippet": "Candidate failed Python screening", "confidence": 0.9, "status": "contradicted"}],
            "status": "contradicted",
        },
        {
            "requirement_id": "req_nice",
            "evidence": [{"snippet": "Recruiter approved Kubernetes certificate", "confidence": 1.0, "status": "verified"}],
            "status": "verified",
        },
    ]
    scored_rejected = score_candidate(cand_reject_must, requirements)
    assert scored_rejected["score"] < scored_both["score"]
    # only nice-to-have verified: 1/3
    assert scored_rejected["score"] == pytest.approx(1 / 3, abs=1e-4)

    # 5. Reject nice-to-have: recruiter marks it "missing" -> score decreases to 0.0
    cand_reject_both = dict(scored_rejected)
    cand_reject_both["matches"] = [
        {
            "requirement_id": "req_must",
            "evidence": [{"snippet": "Candidate failed Python screening", "confidence": 0.9, "status": "contradicted"}],
            "status": "contradicted",
        },
        {
            "requirement_id": "req_nice",
            "evidence": [{"snippet": "No Kubernetes proof", "confidence": 0.0, "status": "missing"}],
            "status": "missing",
        },
    ]
    scored_none = score_candidate(cand_reject_both, requirements)
    assert scored_none["score"] < scored_rejected["score"]
    assert scored_none["score"] == 0.0


def test_score_candidate_with_empty_requirements():
    """Candidate scored against an empty requirements list receives score 0.0 and empty matches."""
    cand = _candidate(skills=["Python"], experience_years=5.0, raw_text="Senior Engineer")
    result = score_candidate(cand, [])
    assert result["score"] == 0.0
    assert result["matches"] == []


def test_score_candidate_uncertain_evidence_earns_zero_points():
    """Uncertain evidence earns no points towards score."""
    requirements = [
        {"id": "req_1", "text": "At least 5 years of Python experience", "type": "must"},
    ]
    cand = _candidate(
        skills=["Python"],
        experience_years=2.0,  # Less than 5 years -> uncertain
        raw_text="2 years of Python experience.",
    )
    result = score_candidate(cand, requirements)
    match = result["matches"][0]
    assert match["status"] == "uncertain"
    assert result["score"] == 0.0


def test_score_candidate_preserves_candidate_attributes():
    """Standard candidate attributes are preserved untouched by score_candidate."""
    requirements = [{"id": "req_1", "text": "Python", "type": "must"}]
    cand = _candidate(
        id="custom_cand_id",
        job_id="custom_job_id",
        name="Custom Candidate",
        email="custom@example.com",
        skills=["Python"],
        experience_years=3.5,
        raw_text="Custom raw text content.",
    )
    result = score_candidate(cand, requirements)
    assert result["id"] == "custom_cand_id"
    assert result["job_id"] == "custom_job_id"
    assert result["name"] == "Custom Candidate"
    assert result["email"] == "custom@example.com"
    assert result["skills"] == ["Python"]
    assert result["experience_years"] == 3.5
    assert result["raw_text"] == "Custom raw text content."
