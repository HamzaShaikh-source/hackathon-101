"""End-to-end API test: create job, upload resumes, fetch candidates, correct a
fact, and export the evidence-backed shortlist report."""

import os
import sys
import tempfile
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# app.main builds the FastAPI app (and calls db.init_db()) at import time, so
# point it at an isolated, throwaway database before importing it.
os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / f"resume_triage_test_{uuid.uuid4().hex}.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

JOB_DESCRIPTION = """Senior Backend Engineer

Must-Have Requirements:
- At least 5 years of professional Python experience
- Experience with FastAPI

Nice-to-Have Requirements:
- Experience with Kubernetes
- Familiarity with AWS
"""

FIXTURE_FILES = ["strong_match.txt", "junior_missing.txt", "contradicted_signal.txt"]


def _create_job() -> dict:
    response = client.post("/api/jobs", json={"description": JOB_DESCRIPTION})
    assert response.status_code == 200
    return response.json()


def _upload_fixtures(job_id: str) -> dict:
    files = [
        ("files", (name, (FIXTURES_DIR / name).read_bytes(), "text/plain"))
        for name in FIXTURE_FILES
    ]
    response = client.post(
        "/api/candidates/upload",
        data={"job_id": job_id},
        files=files,
    )
    assert response.status_code == 200
    return response.json()


def test_full_upload_to_export_flow():
    job = _create_job()
    job_id = job["job_id"]
    assert job_id
    assert any(requirement["type"] == "must" for requirement in job["requirements"])
    assert any(requirement["type"] == "nice" for requirement in job["requirements"])

    upload = _upload_fixtures(job_id)
    candidates = upload["candidates"]
    assert len(candidates) == len(FIXTURE_FILES)
    for candidate in candidates:
        assert candidate["job_id"] == job_id
        assert candidate["matches"], "every candidate should be scored against the requirements"
        assert 0.0 <= candidate["score"] <= 1.0

    # Fetch candidates: the endpoint must rank them by score, descending.
    list_response = client.get(f"/api/jobs/{job_id}/candidates")
    assert list_response.status_code == 200
    ranked = list_response.json()["candidates"]
    assert len(ranked) == len(FIXTURE_FILES)
    scores = [candidate["score"] for candidate in ranked]
    assert scores == sorted(scores, reverse=True)

    names = {candidate["name"]: candidate for candidate in ranked}
    assert "Dana Reyes" in names
    assert "Jamie Lee" in names
    # Strong, explicit resume evidence should outrank a resume with no
    # relevant experience at all.
    assert names["Dana Reyes"]["score"] > names["Jamie Lee"]["score"]

    # Correct a fact on the lowest-scoring candidate and confirm the API
    # recalculates its evidence rather than leaving the old score in place.
    jamie = names["Jamie Lee"]
    patch_response = client.patch(
        f"/api/candidates/{jamie['id']}/facts",
        json={"field": "experience_years", "value": 6},
    )
    assert patch_response.status_code == 200
    corrected = patch_response.json()["candidate"]
    assert corrected["experience_years"] == 6
    assert corrected["score"] > jamie["score"]

    # Export the evidence-backed shortlist report.
    export_response = client.get(f"/api/jobs/{job_id}/export")
    assert export_response.status_code == 200
    markdown = export_response.json()["markdown"]
    assert "Dana Reyes" in markdown
    assert "Jamie Lee" in markdown
    assert "Sam Okafor" in markdown
    assert "decision support" in markdown.lower()
    # Every must-have requirement must cite at least one supporting snippet.
    for requirement in job["requirements"]:
        if requirement["type"] == "must":
            assert requirement["text"] in markdown


def test_export_returns_404_for_unknown_job():
    response = client.get("/api/jobs/does-not-exist/export")
    assert response.status_code == 404
