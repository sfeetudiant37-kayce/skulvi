from __future__ import annotations

import unicodedata
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.catalog import CandidateStatus
from app.repositories import CandidateRepository
from app.schemas import CandidateCreate, CandidateOut, CandidateReviewUpdate, DashboardStats
from app.scoring import score_candidate


class CandidateNotFoundError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_email(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def to_output(record: dict[str, Any]) -> CandidateOut:
    public_record = {key: value for key, value in record.items() if key != "email_normalized"}
    public_record["score"] = score_candidate(record)
    return CandidateOut.model_validate(public_record)


class CandidateService:
    def __init__(self, repository: CandidateRepository):
        self.repository = repository

    def create(self, payload: CandidateCreate, *, is_sample: bool = False) -> CandidateOut:
        data = payload.model_dump(mode="json")
        now = utc_now()
        record = self.repository.create(
            candidate_id=str(uuid4()),
            created_at=now,
            updated_at=now,
            email_normalized=normalize_email(payload.email),
            data=data,
            is_sample=is_sample,
        )
        return to_output(record)

    def get(self, candidate_id: str) -> CandidateOut:
        record = self.repository.get(candidate_id)
        if record is None:
            raise CandidateNotFoundError
        return to_output(record)

    def update_profile(
        self, candidate_id: str, payload: CandidateCreate
    ) -> CandidateOut:
        data = payload.model_dump(mode="json")
        record = self.repository.update_profile(
            candidate_id,
            updated_at=utc_now(),
            email_normalized=normalize_email(payload.email),
            data=data,
        )
        if record is None:
            raise CandidateNotFoundError
        return to_output(record)

    def update_review(
        self, candidate_id: str, payload: CandidateReviewUpdate
    ) -> CandidateOut:
        changes = payload.model_dump(mode="json", exclude_unset=True)
        if "review_notes" in changes and changes["review_notes"] is None:
            changes["review_notes"] = ""
        record = self.repository.update_review(
            candidate_id, updated_at=utc_now(), changes=changes
        )
        if record is None:
            raise CandidateNotFoundError
        return to_output(record)

    def list_page(
        self,
        *,
        query: str | None,
        track: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        records = self.repository.list_candidates(query=query, track=track, status=status)
        candidates = [to_output(record) for record in records]
        candidates.sort(
            key=lambda candidate: (
                candidate.score.triage_index,
                candidate.created_at,
            ),
            reverse=True,
        )
        total = len(candidates)
        start = (page - 1) * page_size
        page_items = candidates[start : start + page_size]
        pages = (total + page_size - 1) // page_size
        return {
            "items": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    def all(self) -> list[CandidateOut]:
        records = self.repository.list_candidates()
        candidates = [to_output(record) for record in records]
        return sorted(
            candidates,
            key=lambda candidate: (candidate.score.triage_index, candidate.created_at),
            reverse=True,
        )

    def stats(self) -> DashboardStats:
        candidates = self.all()
        final_scores = [item.score.final_score for item in candidates if item.score.final_score is not None]
        open_candidates = [item for item in candidates if item.status != CandidateStatus.CLOSED]
        return DashboardStats(
            total=len(candidates),
            priority=sum(item.score.priority_code == "high" for item in open_candidates),
            pending_review=sum(not item.score.review_complete for item in open_candidates),
            shortlisted=sum(item.status == CandidateStatus.SHORTLISTED for item in candidates),
            average_final_score=(round(sum(final_scores) / len(final_scores), 1) if final_scores else None),
        )

    def delete(self, candidate_id: str) -> None:
        if not self.repository.delete(candidate_id):
            raise CandidateNotFoundError
