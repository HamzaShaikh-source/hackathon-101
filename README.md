# Evidence-First Resume Triage

An intelligent resume filtering system that turns resumes into a verifiable hiring work
queue. A recruiter pastes a job description and uploads resumes; the app extracts
structured candidate facts, maps every must-have and nice-to-have requirement to
supporting evidence, and ranks candidates using only verified evidence. Every score is
traceable back to source text, confidence, and any conflicting evidence, so results are
decision support, not an automated hiring decision.

## Features

- **Job intake**: paste a job description and get it parsed into must-have and
  nice-to-have requirements.
- **Resume upload**: upload PDF, DOCX, or TXT resumes and extract structured candidate
  facts (name, email, skills, years of experience).
- **Evidence-backed matching**: each requirement is matched against resume text with a
  supporting snippet, a confidence score, and a status of `verified`, `uncertain`,
  `contradicted`, or `missing`.
- **Deterministic rubric scoring**: candidates are ranked using a fixed rubric over
  verified evidence only — no embeddings, no opaque model scores.
- **Correction queue**: recruiters can correct extracted facts and resolve uncertain or
  contradicted evidence, ordered by likely impact on the ranking; corrections trigger a
  rescore.
- **Evidence-backed export**: generate a shortlist report in Markdown that cites the
  evidence behind every ranked candidate.

## Prerequisites

- Python 3.11+
- pip

## Setup

```bash
cd backend
pip install -r requirements.txt
```

## Running the server

```bash
cd backend
uvicorn app.main:app --port 8000
```

The server reads `PORT` and `DB_PATH` from the environment (defaults: `PORT=8000`,
`DB_PATH=backend/app.db`). The SQLite database file is created automatically on first
run.

## Opening the frontend

The backend serves the frontend as static files from the same app. With the server
running, open:

```
http://localhost:8000/
```

This loads `frontend/index.html`, where a recruiter pastes a job description and
uploads resumes. From there, open the ranking dashboard (`frontend/dashboard.html`) to
review ranked candidates and resolve the evidence queue.

## Running tests

```bash
cd backend
python -m pytest tests -q
```

## Project structure

```
.
├── docs/
│   └── CONTRACT.md          # Frozen API contract: data shapes, endpoints, env vars
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app wiring and static file hosting
│   │   ├── models.py        # Pydantic models: Requirement, Evidence, RequirementMatch, Candidate
│   │   ├── db.py            # SQLite table creation and get/save/list helpers
│   │   ├── routes_jobs.py   # POST /api/jobs — job intake and requirement extraction
│   │   ├── requirements.py  # Requirement extraction logic
│   │   ├── parsing.py       # PDF/DOCX/TXT resume parsing and fact extraction
│   │   ├── routes_upload.py # POST /api/candidates/upload
│   │   ├── scoring.py       # Evidence matching and deterministic rubric scoring
│   │   ├── routes_corrections.py # PATCH/POST endpoints for corrections and recalculation
│   │   └── export.py        # Evidence-backed shortlist report export
│   ├── requirements.txt     # Backend Python dependencies
│   └── tests/                # API and scoring test suite
├── frontend/
│   ├── index.html           # Job description and resume upload UI
│   ├── upload.js
│   ├── styles.css
│   ├── dashboard.html        # Ranking dashboard and evidence queue
│   └── dashboard.js
├── samples/                  # Sample resumes for manual testing and seeding
└── scripts/
    └── seed_samples.py       # Seeds the database with sample jobs and candidates
```

See [docs/CONTRACT.md](docs/CONTRACT.md) for the full API contract: request/response
shapes for every endpoint, the shared scoring function signature, and environment
variables.
