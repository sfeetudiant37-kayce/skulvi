from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import PROJECT_ROOT, Settings
from app.db import Database
from app.repositories import CandidateRepository
from app.seeding import seed_sample_candidates

WEB_ROOT = PROJECT_ROOT / "web"


def create_app(
    database_path: str | Path | None = None,
    *,
    seed_samples: bool | None = None,
) -> FastAPI:
    base_settings = Settings.from_environment()
    settings = replace(
        base_settings,
        database_path=str(database_path or base_settings.database_path),
        seed_sample_data=(
            base_settings.seed_sample_data if seed_samples is None else seed_samples
        ),
    )
    logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))

    application = FastAPI(
        title="Talent Engine API",
        description="API interne de gestion et de qualification des candidatures SKULLVI HCP.",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    database = Database(settings.database_path)
    database.initialize()
    application.state.database = database
    application.state.settings = settings

    if settings.seed_sample_data:
        seeded = seed_sample_candidates(CandidateRepository(database))
        if seeded:
            logging.getLogger(__name__).info("Loaded %s fictional sample candidates", seeded)

    application.include_router(router)
    application.mount("/assets", StaticFiles(directory=WEB_ROOT / "assets"), name="assets")

    @application.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > 2_000_000:
            return JSONResponse({"detail": "La requête dépasse la taille maximale autorisée."}, status_code=413)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        csp = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path == "/api/docs":
            # FastAPI's Swagger UI uses jsDelivr and a small inline initializer.
            csp = (
                "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' data: https://cdn.jsdelivr.net; connect-src 'self'; "
                "object-src 'none'; base-uri 'self'; form-action 'self'"
            )
        response.headers.setdefault("Content-Security-Policy", csp)
        return response

    @application.get("/", include_in_schema=False)
    def homepage() -> FileResponse:
        return FileResponse(
            WEB_ROOT / "index.html",
            media_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    @application.get("/healthz", include_in_schema=False)
    def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @application.get("/readyz", include_in_schema=False)
    def readyz() -> JSONResponse:
        with database.connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return JSONResponse({"status": "ready", "database": "ok"})

    return application

