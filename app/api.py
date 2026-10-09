from __future__ import annotations

import csv
import io
import logging
import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.catalog import CandidateStatus, Track, public_catalog
from app.repositories import CandidateRepository, DuplicateEmailError
from app.schemas import (
    AppMeta,
    CandidateCreate,
    CandidateOut,
    CandidatePage,
    CandidateReviewUpdate,
    DashboardStats,
    HealthStatus,
)
from app.services import CandidateNotFoundError, CandidateService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


def service_for(request: Request) -> CandidateService:
    return CandidateService(CandidateRepository(request.app.state.database))


def spreadsheet_safe(value: object) -> object:
    """Prefix formula-like text so opening a CSV cannot execute it in a spreadsheet."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


@router.get("/health", response_model=HealthStatus, tags=["Operations"])
def health(request: Request) -> HealthStatus:
    try:
        with request.app.state.database.connect() as connection:
            connection.execute("SELECT 1").fetchone()
    except sqlite3.Error as exc:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de données n’est pas disponible.",
        ) from exc
    return HealthStatus(status="ok", database="ok")


@router.get("/meta", response_model=AppMeta, tags=["Operations"])
def metadata(request: Request) -> AppMeta:
    settings = request.app.state.settings
    has_sample_records = any(
        item["is_sample"]
        for item in CandidateRepository(request.app.state.database).list_candidates()
    )
    return AppMeta(environment=settings.environment, sample_data=has_sample_records)


@router.get("/options", tags=["Reference data"])
def options() -> dict[str, object]:
    return public_catalog()


@router.get("/stats", response_model=DashboardStats, tags=["Candidates"])
def stats(request: Request) -> DashboardStats:
    return service_for(request).stats()


@router.get("/candidates/export.csv", tags=["Candidates"])
def export_csv(request: Request) -> Response:
    candidates = service_for(request).all()
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "Nom",
            "E-mail",
            "Parcours",
            "Compétences déclarées",
            "Expérience (non notée)",
            "Disponibilité (non notée)",
            "Projet / contribution",
            "Pré-score compétences /40",
            "Revue projet /25",
            "Motivation /20",
            "Apprentissage /15",
            "Score final /100",
            "Indice de tri /100",
            "Priorité suggérée",
            "Statut",
            "Date de réception",
        ]
    )
    for candidate in candidates:
        writer.writerow(
            spreadsheet_safe(value)
            for value in [
                candidate.name,
                candidate.email,
                candidate.track.value,
                ", ".join([*candidate.skills, candidate.other_skills]).strip(", "),
                candidate.experience_years if candidate.experience_years is not None else "",
                candidate.availability.value if candidate.availability else "",
                candidate.project_summary,
                candidate.score.skill_score,
                candidate.review_project if candidate.review_project is not None else "",
                candidate.review_motivation if candidate.review_motivation is not None else "",
                candidate.review_learning if candidate.review_learning is not None else "",
                candidate.score.final_score if candidate.score.final_score is not None else "",
                candidate.score.triage_index,
                candidate.score.priority_label,
                candidate.status.value,
                candidate.created_at,
            ]
        )
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d")
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="talent-engine-{timestamp}.csv"'},
    )


@router.get("/candidates", response_model=CandidatePage, tags=["Candidates"])
def list_candidates(
    request: Request,
    q: Annotated[str | None, Query(max_length=120)] = None,
    track: Track | None = None,
    status_filter: Annotated[CandidateStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CandidatePage:
    return service_for(request).list_page(
        query=q.strip() if q and q.strip() else None,
        track=track.value if track else None,
        status=status_filter.value if status_filter else None,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/candidates",
    response_model=CandidateOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Candidates"],
)
def create_candidate(payload: CandidateCreate, request: Request) -> CandidateOut:
    try:
        return service_for(request).create(payload)
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un dossier existe déjà pour cette adresse e-mail.",
        ) from exc


@router.get("/candidates/{candidate_id}", response_model=CandidateOut, tags=["Candidates"])
def get_candidate(candidate_id: str, request: Request) -> CandidateOut:
    try:
        return service_for(request).get(candidate_id)
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.") from exc


@router.put("/candidates/{candidate_id}", response_model=CandidateOut, tags=["Candidates"])
def update_candidate(
    candidate_id: str, payload: CandidateCreate, request: Request
) -> CandidateOut:
    service = service_for(request)
    try:
        return service.update_profile(candidate_id, payload)
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.") from exc
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un autre dossier utilise déjà cette adresse e-mail.",
        ) from exc


@router.patch(
    "/candidates/{candidate_id}/review",
    response_model=CandidateOut,
    tags=["Review"],
)
def update_review(
    candidate_id: str, payload: CandidateReviewUpdate, request: Request
) -> CandidateOut:
    try:
        return service_for(request).update_review(candidate_id, payload)
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.") from exc


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Candidates"])
def delete_candidate(candidate_id: str, request: Request) -> Response:
    try:
        service_for(request).delete(candidate_id)
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
