"""FastAPI application entry point for Evidence-First Resume Triage."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from . import db
from .export import router as export_router
from .routes_corrections import router as corrections_router
from .routes_jobs import router as jobs_router
from .routes_upload import router as upload_router


PORT = int(os.environ.get("PORT", "8000"))
_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def create_app() -> FastAPI:
    """Build the API, initialize persistence, and mount the static frontend."""

    configured_db_path = os.environ.get("DB_PATH")
    if configured_db_path:
        db.DB_PATH = configured_db_path
    db.init_db()

    application = FastAPI(
        title="Evidence-First Resume Triage",
        description="Evidence-backed resume ranking for human decision support.",
        version="1.0.0",
    )
    # API routes must be registered before the catch-all static mount.
    application.include_router(jobs_router)
    # routes_jobs owns the shared candidate-list GET. Keep upload's unique
    # multipart route while avoiding a duplicate OpenAPI operation at startup.
    upload_only_router = APIRouter()
    upload_only_router.routes = [
        route
        for route in upload_router.routes
        if getattr(route, "path", "") != "/api/jobs/{job_id}/candidates"
    ]
    application.include_router(upload_only_router)
    application.include_router(corrections_router)
    application.include_router(export_router)

    if not _FRONTEND_DIR.is_dir():
        raise RuntimeError(f"Frontend directory not found: {_FRONTEND_DIR}")
    application.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT)
