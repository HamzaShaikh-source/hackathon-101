"""Evidence-backed shortlist export.

Renders the current ranking for a job as a Markdown report. Every candidate's
score is broken down requirement by requirement, with the cited snippet,
confidence, and status that produced it, so the report can be handed to a
human reviewer as decision support rather than an automated decision.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import get_job, list_candidates

router = APIRouter()

_STATUS_LABELS = {
    "verified": "Verified",
    "uncertain": "Uncertain",
    "contradicted": "Contradicted",
    "missing": "Missing",
}

_DECISION_SUPPORT_NOTICE = (
    "This report is decision support, not an automated hiring decision. "
    "Review every uncertain or contradicted item before acting on this ranking."
)


def _requirement_label(requirement: dict) -> str:
    kind = "must-have" if requirement.get("type") == "must" else "nice-to-have"
    return f"{requirement.get('text', '')} ({kind})"


def _render_requirement_line(requirement: dict, match: dict | None) -> str:
    label = _requirement_label(requirement)
    if match is None or not match.get("evidence"):
        return f"  - **{label}**: _Missing_ — no evidence recorded."

    evidence = match["evidence"][0]
    status = _STATUS_LABELS.get(evidence.get("status"), str(evidence.get("status")))
    confidence = float(evidence.get("confidence") or 0)
    snippet = evidence.get("snippet") or "No supporting resume text found."
    return f'  - **{label}**: {status} ({confidence:.0%} confidence) — "{snippet}"'


def _render_candidate(rank: int, candidate: dict, requirements: list[dict]) -> str:
    matches_by_requirement = {
        str(match.get("requirement_id")): match for match in candidate.get("matches") or []
    }
    lines = [
        f"## {rank}. {candidate.get('name', 'Unknown candidate')} "
        f"(score: {float(candidate.get('score') or 0):.0%})",
        f"- Email: {candidate.get('email', '')}",
        f"- Experience: {float(candidate.get('experience_years') or 0):g} years",
        f"- Skills: {', '.join(candidate.get('skills') or []) or 'None listed'}",
        "- Requirement evidence:",
    ]
    for requirement in requirements:
        requirement_id = str(requirement.get("id"))
        lines.append(_render_requirement_line(requirement, matches_by_requirement.get(requirement_id)))
    return "\n".join(lines)


def build_markdown_report(job: dict, candidates: list[dict]) -> str:
    """Build the evidence-backed shortlist report for a job as Markdown."""

    requirements = job.get("requirements") or []
    lines = [
        f"# Shortlist report: {job.get('description', '').strip().splitlines()[0] if job.get('description') else job.get('id')}",
        "",
        f"_{_DECISION_SUPPORT_NOTICE}_",
        "",
    ]

    if not candidates:
        lines.append("No candidates have been evaluated for this job yet.")
        return "\n".join(lines)

    ranked = sorted(candidates, key=lambda candidate: float(candidate.get("score") or 0), reverse=True)
    for rank, candidate in enumerate(ranked, start=1):
        lines.append(_render_candidate(rank, candidate, requirements))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


@router.get("/api/jobs/{job_id}/export")
def export_shortlist(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    candidates = list_candidates(job_id)
    return {"markdown": build_markdown_report(job, candidates)}
