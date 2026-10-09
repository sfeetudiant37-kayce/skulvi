"""Pure, deterministic qualification rules. No HTTP or database dependencies."""

from __future__ import annotations

import unicodedata
from typing import Any

from app.catalog import TRACK_SKILLS

SKILL_MAX = 40
REVIEW_WEIGHTS = {"project": 25, "motivation": 20, "learning": 15}
REVIEW_MAX = sum(REVIEW_WEIGHTS.values())
FINAL_MAX = SKILL_MAX + REVIEW_MAX


def normalize_skill(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.casefold().strip().split())


def priority_for(index: int) -> tuple[str, str]:
    if index >= 75:
        return "high", "Priorité"
    if index >= 55:
        return "medium", "À examiner"
    return "low", "À compléter"


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return an explainable pre-score, human-review subtotal and triage signal."""
    track = str(candidate.get("track", ""))
    required = TRACK_SKILLS.get(track, [])
    declared = list(candidate.get("skills") or [])
    extra = str(candidate.get("other_skills") or candidate.get("otherSkills") or "")
    declared.extend(skill for skill in extra.split(",") if skill.strip())

    normalized_declared = {normalize_skill(skill) for skill in declared}
    matched = [skill for skill in required if normalize_skill(skill) in normalized_declared]
    skill_score = round(len(matched) / len(required) * SKILL_MAX) if required else 0

    raw_review = {
        "project": candidate.get("review_project", candidate.get("reviewProject")),
        "motivation": candidate.get("review_motivation", candidate.get("reviewMotivation")),
        "learning": candidate.get("review_learning", candidate.get("reviewLearning")),
    }
    review_complete = all(value is not None for value in raw_review.values())
    review_score = sum(value for value in raw_review.values() if isinstance(value, int))
    final_score = skill_score + review_score if review_complete else None
    triage_index = final_score if final_score is not None else round(skill_score / SKILL_MAX * 100)
    priority_code, priority_label = priority_for(triage_index)

    return {
        "matched_skills": matched,
        "skill_score": skill_score,
        "skill_max": SKILL_MAX,
        "review_score": review_score,
        "review_max": REVIEW_MAX,
        "review_complete": review_complete,
        "review_project": raw_review["project"],
        "review_motivation": raw_review["motivation"],
        "review_learning": raw_review["learning"],
        "final_score": final_score,
        "final_max": FINAL_MAX,
        "triage_index": triage_index,
        "priority_code": priority_code,
        "priority_label": priority_label,
    }
