#!/usr/bin/env python3
"""
seed_samples.py - Seeds the Evidence-First Resume Triage API with sample job & resumes.

Per docs/CONTRACT.md:
  1. POST /api/jobs -> {job_id: str, requirements: [Requirement]}
  2. POST /api/candidates/upload -> {candidates: [Candidate]}
  3. GET /api/jobs/{job_id}/candidates -> {candidates: [Candidate]}
"""

import argparse
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

SAMPLE_JOB_DESCRIPTION = """Senior Full-Stack Engineer

About the Role:
We are looking for a Senior Full-Stack Engineer to lead the design and implementation of verifiable, bias-resistant hiring tools. You will build high-throughput APIs and responsive client applications.

Must-Have Requirements:
- At least 4 years of professional software engineering experience
- Strong proficiency in Python and FastAPI or Django
- Hands-on experience building frontend web applications with modern JavaScript / TypeScript and React
- Solid understanding of relational databases and SQL (PostgreSQL or SQLite)

Nice-to-Have Requirements:
- Experience with text parsing, document extraction (PyMuPDF or docx), or NLP
- Familiarity with Docker containerization and CI/CD pipelines
- Background in building accessible and responsive user interfaces
- Previous experience in HR-tech or evidence-based decision support systems
"""


def encode_multipart_formdata(fields: dict, files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    """
    Encodes multipart/form-data using standard library without external dependencies.
    fields: dict of {field_name: field_value}
    files: list of (field_name, filename, file_bytes, content_type)
    """
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()

    # Form fields
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    # Files
    for field_name, filename, content, content_type in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    content_type_header = f"multipart/form-data; boundary={boundary}"
    return bytes(body), content_type_header


def make_request(url: str, method: str = "GET", data: bytes | None = None, headers: dict | None = None) -> tuple[int, dict]:
    """Sends an HTTP request and parses the JSON response."""
    req_headers = headers or {}
    req = Request(url, data=data, headers=req_headers, method=method)

    try:
        with urlopen(req, timeout=30) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            try:
                return status, json.loads(content)
            except json.JSONDecodeError:
                return status, {"raw": content}
    except HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = {"error": err_body}
        return e.code, parsed
    except URLError as e:
        raise ConnectionError(
            f"Could not connect to {url}. Is the backend running? (Error: {e.reason})"
        ) from e


def seed(base_url: str = DEFAULT_BASE_URL, samples_dir: Path | None = None) -> str:
    """Seeds the server with a job and sample resumes."""
    base_url = base_url.rstrip("/")
    if samples_dir is None:
        samples_dir = Path(__file__).resolve().parent.parent / "samples"

    print(f"[*] Target API Base URL: {base_url}")
    print(f"[*] Resumes directory: {samples_dir}")

    # 1. Post Sample Job Description
    print("\n[1/3] Creating sample job description (POST /api/jobs)...")
    job_payload = json.dumps({"description": SAMPLE_JOB_DESCRIPTION}).encode("utf-8")
    status, job_res = make_request(
        f"{base_url}/api/jobs",
        method="POST",
        data=job_payload,
        headers={"Content-Type": "application/json"},
    )

    if status not in (200, 201):
        print(f"[!] Failed to create job (HTTP {status}): {job_res}", file=sys.stderr)
        sys.exit(1)

    job_id = job_res.get("job_id")
    requirements = job_res.get("requirements", [])
    print(f"[+] Job created successfully! ID: {job_id}")
    print(f"[+] Extracted {len(requirements)} requirements:")
    for req in requirements:
        req_type = req.get("type", "must").upper()
        req_text = req.get("text", "")
        print(f"    - [{req_type}] {req_text}")

    # 2. Gather sample resumes
    if not samples_dir.exists():
        print(f"[!] Samples directory not found at: {samples_dir}", file=sys.stderr)
        sys.exit(1)

    resume_files = sorted(list(samples_dir.glob("*.txt")) + list(samples_dir.glob("*.pdf")) + list(samples_dir.glob("*.docx")))
    if not resume_files:
        print(f"[!] No sample resume files found in {samples_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[2/3] Uploading {len(resume_files)} sample resumes (POST /api/candidates/upload)...")
    file_tuples = []
    for r_path in resume_files:
        content = r_path.read_bytes()
        mime_type, _ = mimetypes.guess_type(r_path.name)
        mime_type = mime_type or "text/plain"
        file_tuples.append(("files", r_path.name, content, mime_type))
        print(f"    + Queued: {r_path.name} ({len(content)} bytes)")

    body_bytes, content_type = encode_multipart_formdata(
        fields={"job_id": job_id},
        files=file_tuples,
    )

    status, upload_res = make_request(
        f"{base_url}/api/candidates/upload",
        method="POST",
        data=body_bytes,
        headers={"Content-Type": content_type},
    )

    if status not in (200, 201):
        print(f"[!] Upload failed (HTTP {status}): {upload_res}", file=sys.stderr)
        sys.exit(1)

    uploaded_candidates = upload_res.get("candidates", [])
    print(f"[+] Processed {len(uploaded_candidates)} candidate resumes.")

    # 3. Fetch ranked candidates list
    print(f"\n[3/3] Verifying ranked candidates (GET /api/jobs/{job_id}/candidates)...")
    status, cand_res = make_request(f"{base_url}/api/jobs/{job_id}/candidates")

    if status != 200:
        print(f"[!] Failed to fetch candidates (HTTP {status}): {cand_res}", file=sys.stderr)
        sys.exit(1)

    candidates = cand_res.get("candidates", [])
    print(f"[+] Retrieved {len(candidates)} candidates sorted by score desc:\n")
    print(f"{'Rank':<5} | {'Candidate Name':<22} | {'Exp (Yrs)':<9} | {'Score':<7} | {'Email'}")
    print("-" * 75)
    for idx, c in enumerate(candidates, start=1):
        name = c.get("name", "Unknown")[:20]
        exp = c.get("experience_years", 0.0)
        exp_str = f"{exp:.1f}" if isinstance(exp, (int, float)) else str(exp)
        score = c.get("score", 0.0)
        score_str = f"{score:.1f}" if isinstance(score, (int, float)) else str(score)
        email = c.get("email", "N/A")
        print(f"{idx:<5} | {name:<22} | {exp_str:<9} | {score_str:<7} | {email}")

    print("\n" + "=" * 75)
    print(f"[SUCCESS] Seeding complete!")
    print(f"Job ID: {job_id}")
    print(f"View in Dashboard: {base_url}/dashboard.html?job_id={job_id}")
    print(f"View in Upload UI: {base_url}/index.html?job_id={job_id}")
    print("=" * 75)
    return job_id


def main():
    parser = argparse.ArgumentParser(description="Seed Evidence-First Resume Triage with sample resumes.")
    parser.add_argument(
        "--url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the running API (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--samples",
        type=Path,
        default=None,
        help="Path to directory containing sample resumes (default: samples/)",
    )
    args = parser.parse_args()

    try:
        seed(base_url=args.url, samples_dir=args.samples)
    except ConnectionError as e:
        print(f"\n[!] Connection Error: {e}", file=sys.stderr)
        print("[*] To start the server, run:\n    cd backend && uvicorn app.main:app --port 8000", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
