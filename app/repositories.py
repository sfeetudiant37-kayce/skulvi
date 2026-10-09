from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.db import Database


class DuplicateEmailError(Exception):
    pass


class CandidateRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        record = dict(row)
        record["skills"] = json.loads(record.pop("skills_json"))
        record["is_sample"] = bool(record["is_sample"])
        record.pop("email_normalized", None)
        return record

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0])

    def get(self, candidate_id: str) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
            ).fetchone()
        return self._decode(row)

    def list_candidates(
        self,
        *,
        query: str | None = None,
        track: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if query:
            like = f"%{query.strip()}%"
            clauses.append(
                "(name LIKE ? COLLATE NOCASE OR email LIKE ? COLLATE NOCASE "
                "OR track LIKE ? COLLATE NOCASE OR skills_json LIKE ? COLLATE NOCASE "
                "OR other_skills LIKE ? COLLATE NOCASE)"
            )
            params.extend([like, like, like, like, like])
        if track:
            clauses.append("track = ?")
            params.append(track)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM candidates{where} ORDER BY created_at DESC", params
            ).fetchall()
        return [self._decode(row) for row in rows if row is not None]

    def create(
        self,
        *,
        candidate_id: str,
        created_at: str,
        updated_at: str,
        email_normalized: str,
        data: dict[str, Any],
        is_sample: bool = False,
    ) -> dict[str, Any]:
        sql = """
        INSERT INTO candidates (
            id, created_at, updated_at, name, email, email_normalized, track,
            skills_json, other_skills, experience_years, project_count,
            portfolio_url, project_summary, motivation, availability, status,
            review_project, review_motivation, review_learning, review_notes, is_sample
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', NULL, NULL, NULL, '', ?)
        """
        values = (
            candidate_id,
            created_at,
            updated_at,
            data["name"],
            data["email"],
            email_normalized,
            data["track"],
            json.dumps(data["skills"], ensure_ascii=False),
            data["other_skills"],
            data["experience_years"],
            data["project_count"],
            data["portfolio_url"],
            data["project_summary"],
            data["motivation"],
            data["availability"],
            int(is_sample),
        )
        try:
            with self.database.connect() as connection:
                connection.execute(sql, values)
        except sqlite3.IntegrityError as exc:
            if "email_normalized" in str(exc) or "UNIQUE constraint" in str(exc):
                raise DuplicateEmailError from exc
            raise
        created = self.get(candidate_id)
        assert created is not None
        return created

    def update_profile(
        self,
        candidate_id: str,
        *,
        updated_at: str,
        email_normalized: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        sql = """
        UPDATE candidates SET
            updated_at = ?, name = ?, email = ?, email_normalized = ?, track = ?,
            skills_json = ?, other_skills = ?, experience_years = ?, project_count = ?,
            portfolio_url = ?, project_summary = ?, motivation = ?, availability = ?,
            is_sample = 0
        WHERE id = ?
        """
        values = (
            updated_at,
            data["name"],
            data["email"],
            email_normalized,
            data["track"],
            json.dumps(data["skills"], ensure_ascii=False),
            data["other_skills"],
            data["experience_years"],
            data["project_count"],
            data["portfolio_url"],
            data["project_summary"],
            data["motivation"],
            data["availability"],
            candidate_id,
        )
        try:
            with self.database.connect() as connection:
                cursor = connection.execute(sql, values)
                if cursor.rowcount == 0:
                    return None
        except sqlite3.IntegrityError as exc:
            if "email_normalized" in str(exc) or "UNIQUE constraint" in str(exc):
                raise DuplicateEmailError from exc
            raise
        return self.get(candidate_id)

    def update_review(
        self, candidate_id: str, *, updated_at: str, changes: dict[str, Any]
    ) -> dict[str, Any] | None:
        columns = {
            "review_project": "review_project",
            "review_motivation": "review_motivation",
            "review_learning": "review_learning",
            "review_notes": "review_notes",
            "status": "status",
        }
        assignments = ["updated_at = ?"]
        values: list[Any] = [updated_at]
        for key, value in changes.items():
            column = columns.get(key)
            if column:
                assignments.append(f"{column} = ?")
                values.append(value)
        values.append(candidate_id)
        with self.database.connect() as connection:
            cursor = connection.execute(
                f"UPDATE candidates SET {', '.join(assignments)} WHERE id = ?", values
            )
            if cursor.rowcount == 0:
                return None
        return self.get(candidate_id)

    def delete(self, candidate_id: str) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM candidates WHERE id = ?", (candidate_id,)
            )
        return cursor.rowcount > 0

    def delete_all(self) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute("DELETE FROM candidates")
        return cursor.rowcount
