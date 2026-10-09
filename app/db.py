from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 2 AND 100),
    email TEXT NOT NULL,
    email_normalized TEXT NOT NULL UNIQUE,
    track TEXT NOT NULL CHECK(track IN ('Frontend', 'Backend', 'Full-stack', 'Data / IA', 'QA / Tests', 'DevOps', 'Autre')),
    skills_json TEXT NOT NULL,
    other_skills TEXT NOT NULL DEFAULT '',
    experience_years INTEGER CHECK(experience_years IS NULL OR experience_years BETWEEN 0 AND 40),
    project_count INTEGER NOT NULL DEFAULT 0 CHECK(project_count BETWEEN 0 AND 99),
    portfolio_url TEXT,
    project_summary TEXT NOT NULL DEFAULT '',
    motivation TEXT NOT NULL,
    availability TEXT CHECK(availability IS NULL OR availability IN ('À préciser', 'Moins de 5 h / semaine', '5–9 h / semaine', '10 h ou plus / semaine', 'À discuter')),
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new', 'reviewing', 'shortlisted', 'needs_info', 'closed')),
    review_project INTEGER CHECK(review_project IS NULL OR review_project BETWEEN 0 AND 25),
    review_motivation INTEGER CHECK(review_motivation IS NULL OR review_motivation BETWEEN 0 AND 20),
    review_learning INTEGER CHECK(review_learning IS NULL OR review_learning BETWEEN 0 AND 15),
    review_notes TEXT NOT NULL DEFAULT '',
    is_sample INTEGER NOT NULL DEFAULT 0 CHECK(is_sample IN (0, 1))
);
CREATE INDEX IF NOT EXISTS idx_candidates_track ON candidates(track);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON candidates(created_at DESC);
"""


class Database:
    """Small SQLite adapter with explicit transactions and a versioned schema."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {version} is newer than supported "
                    f"version {SCHEMA_VERSION}."
                )
            if version == 0:
                connection.executescript(SCHEMA)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
