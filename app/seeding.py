from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.repositories import CandidateRepository
from app.schemas import CandidateCreate
from app.services import CandidateService


def seed_sample_candidates(repository: CandidateRepository) -> int:
    """Seed a small, explicitly fictional dataset for preview environments."""
    if repository.count() > 0:
        return 0

    now = datetime.now(UTC)
    samples = [
        {
            "name": "Maya Exemple",
            "email": "maya.frontend@candidats.test",
            "track": "Frontend",
            "skills": ["HTML/CSS", "JavaScript", "React", "Git"],
            "other_skills": "Figma",
            "experience_years": 1,
            "project_count": 2,
            "portfolio_url": "https://example.com/portfolio-maya",
            "project_summary": "Site responsive pour une association : composants React, structure du dépôt, revue des retours utilisateurs et corrections d’accessibilité.",
            "motivation": "Je souhaite renforcer mes bases frontend dans un cadre collaboratif, apprendre à mieux structurer mes projets et recevoir des retours précis sur mon code.",
            "availability": "10 h ou plus / semaine",
            "review_project": 23,
            "review_motivation": 18,
            "review_learning": 14,
            "review_notes": "Exemple fictif : contribution décrite et démarche d’itération à vérifier en entretien.",
            "status": "reviewing",
            "days_ago": 2,
        },
        {
            "name": "Sami Exemple",
            "email": "sami.backend@candidats.test",
            "track": "Backend",
            "skills": ["Python", "SQL", "Git"],
            "other_skills": "Docker",
            "experience_years": 2,
            "project_count": 2,
            "portfolio_url": "https://example.com/api-sami",
            "project_summary": "API de démonstration pour gérer des tâches : routes documentées, base SQL, cas d’erreur et instructions de lancement dans un README.",
            "motivation": "Le programme m’intéresse pour apprendre à travailler en équipe et à concevoir des services utiles. Je veux progresser sur les tests et les bonnes pratiques backend.",
            "availability": "5–9 h / semaine",
            "review_project": 21,
            "review_motivation": 15,
            "review_learning": 11,
            "review_notes": "Exemple fictif : vérifier le rôle exact et la couverture de tests annoncée.",
            "status": "new",
            "days_ago": 4,
        },
        {
            "name": "Lina Exemple",
            "email": "lina.data@candidats.test",
            "track": "Data / IA",
            "skills": ["Python", "SQL", "Excel"],
            "other_skills": "Jupyter",
            "experience_years": 0,
            "project_count": 1,
            "portfolio_url": None,
            "project_summary": "Analyse d’un jeu de données ouvert avec nettoyage des valeurs manquantes, graphiques exploratoires et limites de l’interprétation documentées.",
            "motivation": "J’aimerais apprendre à mieux organiser un projet data, expliquer les résultats simplement et collaborer avec des personnes aux compétences différentes.",
            "availability": "À discuter",
            "review_project": None,
            "review_motivation": None,
            "review_learning": None,
            "review_notes": "",
            "status": "needs_info",
            "days_ago": 1,
        },
        {
            "name": "Alex Exemple",
            "email": "alex.qa@candidats.test",
            "track": "QA / Tests",
            "skills": ["JavaScript", "Git"],
            "other_skills": "",
            "experience_years": None,
            "project_count": 0,
            "portfolio_url": None,
            "project_summary": "",
            "motivation": "Je veux découvrir les tests logiciels et apprendre à repérer les erreurs avant la mise en production.",
            "availability": "Moins de 5 h / semaine",
            "review_project": None,
            "review_motivation": None,
            "review_learning": None,
            "review_notes": "",
            "status": "new",
            "days_ago": 6,
        },
    ]

    service = CandidateService(repository)
    for sample in samples:
        days_ago = sample.pop("days_ago")
        review_changes = {
            "review_project": sample.pop("review_project"),
            "review_motivation": sample.pop("review_motivation"),
            "review_learning": sample.pop("review_learning"),
            "review_notes": sample.pop("review_notes"),
            "status": sample.pop("status"),
        }
        record = CandidateCreate.model_validate(sample)
        created = service.create(record, is_sample=True)
        created_at = (now - timedelta(days=days_ago)).isoformat(timespec="seconds").replace("+00:00", "Z")
        repository.update_review(created.id, updated_at=created_at, changes=review_changes)
        with repository.database.connect() as connection:
            connection.execute(
                "UPDATE candidates SET created_at = ?, updated_at = ? WHERE id = ?",
                (created_at, created_at, created.id),
            )
    return len(samples)
