"""Deterministic evidence matching and rubric scoring.

The scorer intentionally uses lexical rules rather than embeddings.  Every
match contains the text that caused the decision, making the result suitable
for human review and correction before it is used for ranking.
"""

from __future__ import annotations

import re
from typing import Any


_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#./-]*", re.IGNORECASE)
_YEARS_RE = re.compile(r"(?P<number>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "for", "from",
    "have", "in", "is", "of", "on", "or", "our", "should", "that", "the", "their",
    "this", "to", "we", "with", "will", "you", "your", "years", "year", "experience",
}
_NEGATION_RE = re.compile(
    r"\b(?:no|not|never|without|lacks?|lack(?:ing)?|doesn['’]?t|didn['’]?t)\b",
    re.IGNORECASE,
)


def _tokens(value: Any) -> set[str]:
    """Return normalized, useful tokens while keeping technology punctuation."""

    tokens = set()
    for token in _TOKEN_RE.findall(str(value or "").lower()):
        token = token.strip(".-")
        if len(token) > 1 and token not in _STOP_WORDS:
            tokens.add(token)
            if token.endswith("ies") and len(token) > 4:
                tokens.add(token[:-3] + "y")
            elif token.endswith("s") and not token.endswith(("ss", "us")):
                tokens.add(token[:-1])
    return tokens


def _sentences(raw_text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?\n])\s+", raw_text or "") if sentence.strip()]


def _experience_requirement(text: str) -> float | None:
    matches = list(_YEARS_RE.finditer(text or ""))
    if not matches:
        return None
    # A requirement can say "3-5 years"; the minimum is the first value.
    return float(matches[0].group("number"))


def _experience_evidence(candidate: dict, requirement: dict) -> tuple[str, float, str] | None:
    minimum = _experience_requirement(str(requirement.get("text", "")))
    if minimum is None:
        return None
    actual = float(candidate.get("experience_years") or 0)
    source = f"{actual:g} years of experience (extracted candidate fact); requirement: {minimum:g}+ years"
    if actual >= minimum:
        return source, 0.98, "verified"
    if actual > 0:
        return source, 0.76, "uncertain"
    return source, 0.55, "missing"


def _supporting_snippet(raw_text: str, matched: set[str], skills: list[str]) -> str:
    sentences = _sentences(raw_text)
    if matched:
        ranked = sorted(
            sentences,
            key=lambda sentence: len(matched & _tokens(sentence)),
            reverse=True,
        )
        if ranked and matched & _tokens(ranked[0]):
            return ranked[0][:400]
    for skill in skills:
        if _tokens(skill) & matched:
            return f"Listed skill: {skill}"
    return "No supporting resume text found."


def _is_negated(sentence: str, matched: set[str]) -> bool:
    if not matched or not _NEGATION_RE.search(sentence):
        return False
    # Negation within the same sentence is a conservative contradiction signal.
    # It catches common resume phrasing such as "no experience with Tableau".
    return bool(matched & _tokens(sentence))


def _automatic_match(candidate: dict, requirement: dict) -> dict:
    text = str(requirement.get("text", ""))
    raw_text = str(candidate.get("raw_text", "") or "")
    skills = [str(skill) for skill in (candidate.get("skills") or [])]
    required = _tokens(text)
    source_tokens = _tokens(raw_text) | set().union(*(_tokens(skill) for skill in skills)) if skills else _tokens(raw_text)
    matched = required & source_tokens
    experience = _experience_evidence(candidate, requirement)
    if experience is not None:
        snippet, confidence, status = experience
        return {"snippet": snippet, "confidence": confidence, "status": status}

    if not required:
        return {"snippet": "Requirement has no matchable keywords.", "confidence": 0.0, "status": "missing"}

    overlap = len(matched) / len(required)
    relevant_sentence = max(
        _sentences(raw_text),
        key=lambda sentence: len(matched & _tokens(sentence)),
        default="",
    )
    if _is_negated(relevant_sentence, matched):
        status, confidence = "contradicted", min(0.94, 0.72 + overlap * 0.2)
    elif overlap >= 0.7 or (len(required) == 1 and overlap == 1):
        status, confidence = "verified", min(0.98, 0.78 + overlap * 0.2)
    elif overlap > 0:
        status, confidence = "uncertain", min(0.74, 0.42 + overlap * 0.3)
    else:
        status, confidence = "missing", 0.0
    return {
        "snippet": _supporting_snippet(raw_text, matched, skills),
        "confidence": round(confidence, 2),
        "status": status,
    }


def _existing_decision(candidate: dict, requirement_id: str) -> dict | None:
    """Return an existing human decision so corrections survive rescoring."""

    for match in candidate.get("matches") or []:
        if str(match.get("requirement_id")) != requirement_id:
            continue
        evidence = match.get("evidence") or []
        for item in evidence:
            status = item.get("status")
            if status in {"verified", "contradicted", "uncertain", "missing"}:
                return {
                    "snippet": str(item.get("snippet") or "No supporting resume text found."),
                    "confidence": round(max(0.0, min(1.0, float(item.get("confidence") or 0))), 2),
                    "status": status,
                }
    return None


def score_candidate(candidate: dict, requirements: list[dict]) -> dict:
    """Populate ``candidate`` matches and score it using verified evidence only.

    Must-have requirements are worth two points and nice-to-have requirements
    one point.  A missing, uncertain, or contradicted requirement earns no
    points; this makes an unsupported match unable to improve a ranking.
    Existing evidence statuses are treated as recruiter decisions and are
    preserved across recalculation.
    """

    matches = []
    earned = 0.0
    possible = 0.0
    for requirement in requirements or []:
        requirement_id = str(requirement.get("id", ""))
        weight = 2.0 if requirement.get("type") == "must" else 1.0
        evidence = _existing_decision(candidate, requirement_id) or _automatic_match(candidate, requirement)
        evidence = {
            "snippet": evidence["snippet"],
            "confidence": round(max(0.0, min(1.0, float(evidence["confidence"]))), 2),
            "status": evidence["status"],
        }
        matches.append({"requirement_id": requirement_id, "evidence": [evidence], "status": evidence["status"]})
        possible += weight
        if evidence["status"] == "verified":
            earned += weight

    candidate["matches"] = matches
    candidate["score"] = round(earned / possible, 4) if possible else 0.0
    return candidate
