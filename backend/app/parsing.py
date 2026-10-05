"""Resume parsing and fact extraction engine.

Extracts raw text from .pdf (PyMuPDF), .docx (python-docx), and .txt files,
and extracts candidate name, email, skills, and experience_years using regex and heuristics.
"""

import io
import re
from datetime import datetime
from typing import Any

# PyMuPDF import
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

# python-docx import
try:
    import docx
except ImportError:
    docx = None

# Known technical skills catalog
KNOWN_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "Next.js", "Vue.js", "Angular",
    "Node.js", "FastAPI", "Django", "Flask", "Express", "SQL", "PostgreSQL",
    "MySQL", "SQLite", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", "GCP",
    "Azure", "Git", "GitHub Actions", "Linux", "HTML", "HTML5", "CSS", "CSS3",
    "Tailwind CSS", "SCSS", "PyTest", "Celery", "GraphQL", "REST APIs", "REST",
    "PyMuPDF", "python-docx", "spaCy", "Pandas", "NumPy", "PyTorch", "TensorFlow",
    "Scikit-Learn", "HuggingFace", "Java", "C++", "C#", "Go", "Rust", "Ruby",
    "PHP", "Bash", "Shell", "CI/CD", "Redux", "Zustand", "Material UI", "Vite",
    "Kafka", "Elasticsearch", "Selenium", "Postman", "Bootstrap"
]


def extract_raw_text(file_bytes: bytes, filename: str) -> str:
    """Extract raw text from PDF, DOCX, or TXT file bytes."""
    ext = ("." + filename.split(".")[-1].lower()) if "." in filename else ""

    if ext == ".pdf":
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is not installed.")
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = [page.get_text() for page in doc]
        return "\n".join(pages).strip()

    elif ext == ".docx":
        if docx is None:
            raise RuntimeError("python-docx is not installed.")
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        # Also include table text if present
        table_text = []
        for table in doc.tables:
            for row in table.rows:
                row_str = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_str:
                    table_text.append(row_str)
        all_text = paragraphs + table_text
        return "\n".join(all_text).strip()

    else:
        # Default text-based decoding
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return file_bytes.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return file_bytes.decode("utf-8", errors="replace").strip()


def extract_email(text: str) -> str:
    """Extract first valid email address from resume text."""
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(pattern, text)
    if matches:
        return matches[0].strip()
    return ""


def extract_name(text: str) -> str:
    """Extract candidate name using labeled prefixes or top header lines."""
    # 1. Look for explicit name prefix: Name: John Doe or Candidate: John Doe
    labeled_match = re.search(
        r"^(?:Name\s*[:\-]\s*|\bCandidate\s*[:\-]\s*)([A-Z][a-zA-Z\s\.\'\-]+)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if labeled_match:
        cand_name = labeled_match.group(1).strip()
        words = cand_name.split()
        if 2 <= len(words) <= 4:
            return cand_name

    # 2. Inspect first non-empty lines before contact details or sections
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    ignore_words = {
        "resume", "curriculum", "vitae", "cv", "profile", "contact", "summary",
        "experience", "education", "skills", "objective", "page", "phone", "email"
    }

    for line in lines[:8]:
        # Strip phone numbers, emails, URLs, special chars
        cleaned = re.sub(r"[0-9\(\)\+\@\:\/\#\-\|\,\.\;]", " ", line)
        words = [w for w in cleaned.split() if len(w) > 1]

        if 2 <= len(words) <= 4:
            # Check if any word is a common header word
            if any(w.lower() in ignore_words for w in words):
                continue
            # Check capitalization
            if all(w[0].isupper() for w in words):
                return " ".join(words)

    # Fallback to first line if it looks like a single or double word
    if lines:
        first_clean = re.sub(r"[^a-zA-Z\s]", "", lines[0]).strip()
        words = first_clean.split()
        if 1 <= len(words) <= 4 and not any(w.lower() in ignore_words for w in words):
            return " ".join(words)

    return "Unknown Candidate"


def extract_experience_years(text: str) -> float:
    """Extract years of experience via explicit mentions or work history date spans."""
    explicit_matches = re.findall(
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+professional|\s+industry|\s+hands-on|\s+specialized)?\s+experience",
        text,
        re.IGNORECASE,
    )
    explicit_vals = [float(m) for m in explicit_matches if 0 < float(m) < 45]

    # Date range heuristic: e.g. "2018 - 2021" or "March 2021 - Present"
    date_pattern = (
        r"(?:\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?"
        r"(20\d\d|19\d\d)\s*[-–—to]+\s*"
        r"(?:(?:\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(20\d\d|19\d\d)|Present|Current)"
    )
    ranges = re.findall(date_pattern, text, re.IGNORECASE)

    current_year = datetime.now().year
    calculated_total = 0.0

    for start_str, end_str in ranges:
        try:
            start_yr = int(start_str)
            if not end_str or end_str.lower() in ("present", "current"):
                end_yr = current_year
            else:
                end_yr = int(end_str)

            if 1980 <= start_yr <= end_yr <= current_year + 1:
                diff = end_yr - start_yr
                if diff <= 30:
                    calculated_total += max(diff, 1)
        except (ValueError, TypeError):
            continue

    if explicit_vals:
        return float(max(explicit_vals))
    if calculated_total > 0:
        return float(calculated_total)
    return 0.0


def extract_skills(text: str) -> list[str]:
    """Extract technical skills using known skills catalog and skills section parser."""
    found_skills: dict[str, str] = {}  # lowercase -> formatted

    # 1. Match against KNOWN_SKILLS catalog with word boundaries
    for skill in KNOWN_SKILLS:
        # Regex matching skill name case-insensitively with word boundaries
        escaped = re.escape(skill)
        pattern = rf"\b{escaped}\b"
        if re.search(pattern, text, re.IGNORECASE):
            found_skills[skill.lower()] = skill

    # 2. Extract from explicit Skills section if present
    section_match = re.search(
        r"(?:TECHNICAL\s+SKILLS|SKILLS|CORE\s+COMPETENCIES|EXPERTISE)\s*[:\n](.*?)(?:\n\s*[A-Z\s]{4,}|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if section_match:
        sec_text = section_match.group(1)
        # Split tokens by common delimiters
        tokens = re.split(r"[,•|;\n\-]+", sec_text)
        for tok in tokens:
            cleaned = tok.strip()
            # Strip prefixes like "Languages:" or "Databases:"
            cleaned = re.sub(r"^[a-zA-Z\s&]+:\s*", "", cleaned).strip()
            if 2 <= len(cleaned) <= 25:
                # Discard noise words
                if not any(w in cleaned.lower() for w in ["university", "bachelor", "master", "present", "experience", "lead", "engineer"]):
                    if cleaned.lower() not in found_skills:
                        found_skills[cleaned.lower()] = cleaned

    return list(found_skills.values())


def parse_resume(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Complete resume extraction returning parsed facts."""
    raw_text = extract_raw_text(file_bytes, filename)
    name = extract_name(raw_text)
    email = extract_email(raw_text)
    skills = extract_skills(raw_text)
    experience_years = extract_experience_years(raw_text)

    return {
        "name": name,
        "email": email,
        "skills": skills,
        "experience_years": experience_years,
        "raw_text": raw_text,
    }
