from app.scoring import priority_for, score_candidate


def test_skill_match_is_case_and_accent_insensitive() -> None:
    result = score_candidate(
        {
            "track": "Frontend",
            "skills": ["html/css", "JAVASCRIPT", "réact"],
            "other_skills": "",
        }
    )
    assert result["matched_skills"] == ["HTML/CSS", "JavaScript", "React"]
    assert result["skill_score"] == 30


def test_human_review_is_required_for_final_score() -> None:
    result = score_candidate(
        {
            "track": "Frontend",
            "skills": ["HTML/CSS", "JavaScript", "React", "Git"],
            "review_project": 20,
            "review_motivation": None,
            "review_learning": 10,
        }
    )
    assert result["review_score"] == 30
    assert result["review_complete"] is False
    assert result["final_score"] is None
    assert result["triage_index"] == 100


def test_final_score_and_priority_are_deterministic() -> None:
    result = score_candidate(
        {
            "track": "Frontend",
            "skills": ["HTML/CSS", "JavaScript", "React", "Git"],
            "review_project": 20,
            "review_motivation": 15,
            "review_learning": 12,
        }
    )
    assert result["final_score"] == 87
    assert result["triage_index"] == 87
    assert result["priority_code"] == "high"


def test_priority_thresholds_are_explicit() -> None:
    assert priority_for(75) == ("high", "Priorité")
    assert priority_for(74) == ("medium", "À examiner")
    assert priority_for(54) == ("low", "À compléter")
