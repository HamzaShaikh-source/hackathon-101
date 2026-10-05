"""Job requirement extraction engine using deterministic heuristics.

Splits a pasted job description into must/nice requirements based on
section headers, bullet lines, and explicit keywords.
"""

import re
from typing import List

from app.models import Requirement, RequirementType

# Section header patterns - checked NICE first so "Bonus Qualifications" is recognized as nice
NICE_SECTION_RE = re.compile(
    r"(?:nice[- ](?:to[- ])?have|preferred|bonus|plus(?:es)?|desired|good to have|optional|advantageous|would be great)",
    re.IGNORECASE,
)
MUST_SECTION_RE = re.compile(
    r"(?:must[- ](?:to[- ])?have|must[- ]have|minimum|basic|required|requirements|what you(?:'ll)? need|qualifications|core requirements)",
    re.IGNORECASE,
)
SECTION_HEADER_RE = re.compile(
    r"^(?:[A-Z0-9\s/&-]+:|\s*#{1,4}\s+.*|[A-Za-z\s/&-]{3,40}:)$",
    re.MULTILINE,
)

# Line-level keywords
NICE_KEYWORD_RE = re.compile(
    r"\b(?:preferred|nice to have|bonus|plus|optional|desired|ideal|familiarity with|advantage)\b",
    re.IGNORECASE,
)
MUST_KEYWORD_RE = re.compile(
    r"\b(?:must|required|essential|minimum|mandatory|at least \d|proficiency in)\b",
    re.IGNORECASE,
)

# Bullet prefix remover - only strips digits if followed by punctuation like . or )
BULLET_PREFIX_RE = re.compile(
    r"^(?:[\s*•–—\-\[\]\>]+|\d+[\.\)\:\-\]]\s*)",
)


def extract_requirements(job_description: str) -> List[Requirement]:
    """Parse a job description string and extract a list of structured Requirement models."""
    lines = job_description.splitlines()
    requirements: List[Requirement] = []

    current_section_type: RequirementType | None = None
    req_index = 1

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        # Check if line looks like a section header
        is_header = (
            trimmed.endswith(":")
            or trimmed.startswith("#")
            or SECTION_HEADER_RE.match(trimmed)
            or (len(trimmed) < 40 and trimmed.isupper())
        )

        if is_header:
            if NICE_SECTION_RE.search(trimmed):
                current_section_type = "nice"
            elif MUST_SECTION_RE.search(trimmed):
                current_section_type = "must"
            else:
                # Other section (e.g. "About Us:", "Responsibilities:")
                current_section_type = None
            continue

        # Check if line is a bullet item
        is_bullet = bool(re.match(r"^[\s*•–—\-\[\]\>]\s*", line) or re.match(r"^\s*\d+[\.\)\:\-]\s*", line))
        cleaned_text = BULLET_PREFIX_RE.sub("", trimmed).strip()

        # Ignore empty lines
        if len(cleaned_text) < 2:
            continue

        # Determine if this line represents a requirement
        req_type: RequirementType | None = None

        if current_section_type is not None and is_bullet:
            req_type = current_section_type
            # Keyword overrides inside section
            if NICE_KEYWORD_RE.search(cleaned_text):
                req_type = "nice"
            elif MUST_KEYWORD_RE.search(cleaned_text):
                req_type = "must"

        elif is_bullet:
            # Bullet point outside explicit section
            if NICE_KEYWORD_RE.search(cleaned_text):
                req_type = "nice"
            elif MUST_KEYWORD_RE.search(cleaned_text):
                req_type = "must"
            else:
                # Default bullet items to 'must'
                req_type = "must"

        else:
            # Non-bullet line with explicit requirement keywords
            if NICE_KEYWORD_RE.search(cleaned_text):
                req_type = "nice"
            elif MUST_KEYWORD_RE.search(cleaned_text):
                req_type = "must"

        if req_type is not None:
            requirements.append(
                Requirement(
                    id=f"req_{req_index}",
                    text=cleaned_text,
                    type=req_type,
                )
            )
            req_index += 1

    # Fallback: if no requirements detected, split lines and generate default must requirements
    if not requirements:
        for line in lines:
            trimmed = line.strip()
            if len(trimmed) > 15:
                cleaned = BULLET_PREFIX_RE.sub("", trimmed).strip()
                requirements.append(
                    Requirement(
                        id=f"req_{req_index}",
                        text=cleaned,
                        type="must",
                    )
                )
                req_index += 1
                if len(requirements) >= 5:
                    break

    return requirements
