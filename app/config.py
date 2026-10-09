from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    database_path: str = str(PROJECT_ROOT / "data" / "talent_engine.sqlite3")
    seed_sample_data: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            environment=os.getenv("APP_ENV", "development").strip().lower(),
            database_path=os.getenv(
                "DATABASE_PATH", str(PROJECT_ROOT / "data" / "talent_engine.sqlite3")
            ),
            seed_sample_data=os.getenv("SEED_SAMPLE_DATA", "false").strip().lower()
            in {"1", "true", "yes", "on"},
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        )
