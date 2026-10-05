# hackathon 101

We are building Evidence-First Resume Triage: a FastAPI + SQLite backend that parses a pasted job description into must/nice requirements, extracts structured facts from uploaded PDF/DOCX/TXT resumes, maps each requirement to supporting snippets with confidence and verified/uncertain/contradicted/missing status using a deterministic rubric (no embeddings), and a static HTML/JS frontend where recruiters upload resumes, review the ranked shortlist, resolve uncertain evidence, and export a defensible report. All pieces talk through the fixed JSON API in docs/CONTRACT.md so backend modules, scoring, and frontend can be built in parallel.

Stack: Python 3.11 + FastAPI + Uvicorn + SQLite for the backend (PyMuPDF for PDF text, python-docx for DOCX, no embeddings/pgvector per risk mitigation); plain HTML/CSS/JS (no build step) for the frontend served as static files by FastAPI. Run: cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000, then open http://localhost:8000/.

Verification: `cd backend && python -m pytest tests -q`

| Task | Title | Owner | Files | Depends on |
|---|---|---|---|---|
| T1 | Core data models and SQLite storage | HamzaShaikh-source | backend/app/models.py, backend/app/db.py | - |
| T2 | Job intake and requirement extraction | Nishitha's MacBook | backend/app/routes_jobs.py, backend/app/requirements.py | T1 |
| T3 | Resume parsing and fact extraction | Nishitha's MacBook | backend/app/parsing.py, backend/app/routes_upload.py | T1 |
| T4 | Evidence matching and rubric scoring engine | Jyoti's desktop | backend/app/scoring.py | T1 |
| T5 | Corrections and recalculation API | Jyoti's desktop | backend/app/routes_corrections.py | T4 |
| T6 | Evidence-backed shortlist export | HamzaShaikh-source | backend/app/export.py | T4 |
| T7 | App wiring, static hosting, and dependencies | Jyoti's desktop | backend/app/main.py, backend/requirements.txt, backend/app/__init__.py | T2, T3, T5, T6 |
| T8 | Frontend: job description and resume upload UI | Nishitha's MacBook | frontend/index.html, frontend/upload.js, frontend/styles.css | - |
| T9 | Frontend: ranking dashboard and evidence queue | Jyoti's desktop | frontend/dashboard.html, frontend/dashboard.js | - |
| T10 | Automated tests for API and scoring | HamzaShaikh-source | backend/tests/test_api.py, backend/tests/test_scoring.py, backend/tests/fixtures/* | T7 |
| T11 | README and project documentation | HamzaShaikh-source | README.md | - |
| T12 | Sample resumes and seed script | Nishitha's MacBook | samples/*.txt, scripts/seed_samples.py | - |
