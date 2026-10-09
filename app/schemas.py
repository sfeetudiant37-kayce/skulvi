from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from app.catalog import Availability, CandidateStatus, Track

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


class CandidateCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=160)
    track: Track
    skills: list[str] = Field(default_factory=list, max_length=20)
    other_skills: str = Field(default="", max_length=300)
    experience_years: int | None = Field(default=None, ge=0, le=40)
    project_count: int = Field(default=0, ge=0, le=99)
    portfolio_url: str | None = Field(default=None, max_length=300)
    project_summary: str = Field(default="", max_length=1400)
    motivation: str = Field(min_length=30, max_length=1400)
    availability: Availability | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not _EMAIL_RE.fullmatch(cleaned):
            raise ValueError("Saisissez une adresse e-mail valide.")
        return cleaned

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            skill = value.strip()
            if not skill or len(skill) > 50:
                raise ValueError("Chaque compétence doit contenir entre 1 et 50 caractères.")
            key = skill.casefold()
            if key not in seen:
                cleaned.append(skill)
                seen.add(key)
        return cleaned

    @field_validator("portfolio_url")
    @classmethod
    def validate_portfolio_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        try:
            parsed = urlsplit(cleaned)
            valid_host = bool(parsed.hostname) and "." in parsed.hostname
            valid_scheme = parsed.scheme in {"http", "https"}
            # Accessing .port validates malformed port numbers too.
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("Le lien doit être une URL HTTP(S) valide.") from exc
        if not valid_host or not valid_scheme:
            raise ValueError("Le lien doit commencer par http:// ou https://.")
        return cleaned

    @model_validator(mode="after")
    def require_at_least_one_skill(self) -> CandidateCreate:
        if not self.skills and not self.other_skills.strip():
            raise ValueError("Indiquez au moins une compétence.")
        return self


class CandidateReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_project: StrictInt | None = Field(default=None, ge=0, le=25)
    review_motivation: StrictInt | None = Field(default=None, ge=0, le=20)
    review_learning: StrictInt | None = Field(default=None, ge=0, le=15)
    review_notes: str | None = Field(default=None, max_length=2000)
    status: CandidateStatus | None = None

    @model_validator(mode="after")
    def validate_patch_values(self) -> CandidateReviewUpdate:
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Le statut ne peut pas être vide.")
        return self


class ScoreSummary(BaseModel):
    matched_skills: list[str]
    skill_score: int
    skill_max: int
    review_score: int
    review_max: int
    review_complete: bool
    review_project: int | None
    review_motivation: int | None
    review_learning: int | None
    final_score: int | None
    final_max: int
    triage_index: int
    priority_code: str
    priority_label: str


class CandidateOut(BaseModel):
    id: str
    created_at: str
    updated_at: str
    name: str
    email: str
    track: Track
    skills: list[str]
    other_skills: str
    experience_years: int | None
    project_count: int
    portfolio_url: str | None
    project_summary: str
    motivation: str
    availability: Availability | None
    status: CandidateStatus
    review_project: int | None
    review_motivation: int | None
    review_learning: int | None
    review_notes: str
    is_sample: bool
    score: ScoreSummary


class CandidatePage(BaseModel):
    items: list[CandidateOut]
    total: int
    page: int
    page_size: int
    pages: int


class DashboardStats(BaseModel):
    total: int
    priority: int
    pending_review: int
    shortlisted: int
    average_final_score: float | None


class HealthStatus(BaseModel):
    status: str
    database: str


class AppMeta(BaseModel):
    environment: str
    sample_data: bool


class CatalogResponse(BaseModel):
    tracks: list[dict[str, Any]]
    statuses: list[dict[str, str]]
    availability: list[str]
