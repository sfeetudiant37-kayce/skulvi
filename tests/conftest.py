from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    app = create_app(tmp_path / "test.sqlite3", seed_samples=False)
    with TestClient(app) as test_client:
        yield test_client


def candidate_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Camille Exemple",
        "email": "camille@example.test",
        "track": "Frontend",
        "skills": ["HTML/CSS", "JavaScript", "Git"],
        "other_skills": "",
        "experience_years": 1,
        "project_count": 1,
        "portfolio_url": "https://example.test/portfolio",
        "project_summary": "Application responsive avec une contribution personnelle claire.",
        "motivation": "Je veux progresser en équipe et apprendre à livrer des fonctionnalités utiles.",
        "availability": "5–9 h / semaine",
    }
    payload.update(overrides)
    return payload
