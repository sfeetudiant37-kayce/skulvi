from enum import StrEnum


class Track(StrEnum):
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    FULLSTACK = "Full-stack"
    DATA = "Data / IA"
    QA = "QA / Tests"
    DEVOPS = "DevOps"
    OTHER = "Autre"


TRACK_SKILLS: dict[str, list[str]] = {
    Track.FRONTEND.value: ["HTML/CSS", "JavaScript", "React", "Git"],
    Track.BACKEND.value: ["Python", "Node.js", "SQL", "Git"],
    Track.FULLSTACK.value: ["HTML/CSS", "JavaScript", "SQL", "Git"],
    Track.DATA.value: ["Python", "SQL", "Excel", "Power BI"],
    Track.QA.value: ["Tests automatisés", "JavaScript", "Python", "Git"],
    Track.DEVOPS.value: ["Linux", "Docker", "Git", "Cloud"],
    Track.OTHER.value: ["Documentation", "Communication", "Résolution de problèmes", "Git"],
}


class CandidateStatus(StrEnum):
    NEW = "new"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    NEEDS_INFO = "needs_info"
    CLOSED = "closed"


STATUS_LABELS: dict[str, str] = {
    CandidateStatus.NEW.value: "Nouveau",
    CandidateStatus.REVIEWING.value: "En analyse",
    CandidateStatus.SHORTLISTED.value: "Présélectionné",
    CandidateStatus.NEEDS_INFO.value: "À compléter",
    CandidateStatus.CLOSED.value: "Clôturé",
}


class Availability(StrEnum):
    TO_CONFIRM = "À préciser"
    LESS_THAN_FIVE = "Moins de 5 h / semaine"
    FIVE_TO_NINE = "5–9 h / semaine"
    TEN_OR_MORE = "10 h ou plus / semaine"
    DISCUSS = "À discuter"


def public_catalog() -> dict[str, object]:
    return {
        "tracks": [
            {"value": track.value, "skills": TRACK_SKILLS[track.value]}
            for track in Track
        ],
        "statuses": [
            {"value": status.value, "label": STATUS_LABELS[status.value]}
            for status in CandidateStatus
        ],
        "availability": [item.value for item in Availability],
    }
