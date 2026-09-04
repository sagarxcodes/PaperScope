"""
PaperScope — Generic Exam Intelligence Engine

IMPORTANT:
- No exam syllabus is hard-coded here.
- Exam data is supplied through versioned exam profiles.
- The engine only validates, normalizes and plans assessments.
- This allows TNPSC, NEET, JEE, UPSC, GATE, CAT, etc. to be added
  or updated without changing the intelligence engine.
"""

from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, List, Optional


SUPPORTED_MODES = {
    "targeted",
    "weak_topic",
    "subject_test",
    "full_mock",
}


def normalize_exam_id(exam: str) -> str:
    """Create a stable exam identifier."""
    return (
        str(exam or "")
        .strip()
        .upper()
        .replace("-", "_")
        .replace(" ", "_")
    )


def validate_exam_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a dynamically supplied exam profile.

    The profile can come from:
    - an official-source ingestion service
    - a stored/versioned JSON document
    - an admin-managed exam registry
    - an external exam API
    """

    if not isinstance(profile, dict):
        raise ValueError("Exam profile must be an object.")

    required = ["id", "name", "version"]

    missing = [
        field
        for field in required
        if not profile.get(field)
    ]

    if missing:
        raise ValueError(
            f"Exam profile missing required fields: {', '.join(missing)}"
        )

    normalized = deepcopy(profile)

    normalized["id"] = normalize_exam_id(profile["id"])
    normalized["name"] = str(profile["name"]).strip()
    normalized["version"] = str(profile["version"]).strip()

    normalized.setdefault("subjects", [])
    normalized.setdefault("syllabus", {})
    normalized.setdefault("assessment", {})
    normalized.setdefault("sources", [])

    if not isinstance(normalized["subjects"], list):
        normalized["subjects"] = []

    if not isinstance(normalized["syllabus"], dict):
        normalized["syllabus"] = {}

    if not isinstance(normalized["assessment"], dict):
        normalized["assessment"] = {}

    return normalized


def get_syllabus_taxonomy(
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Return the normalized syllabus taxonomy.

    Expected structure is intentionally flexible:

    {
        "Subject": {
            "Topic": ["Subtopic", "..."]
        }
    }

    or:

    {
        "Subject": ["Topic", "..."]
    }
    """

    profile = validate_exam_profile(profile)

    return deepcopy(profile.get("syllabus", {}))


def flatten_syllabus(
    profile: Dict[str, Any],
) -> List[Dict[str, Optional[str]]]:
    """Convert a hierarchical syllabus into searchable competency nodes."""

    syllabus = get_syllabus_taxonomy(profile)
    nodes: List[Dict[str, Optional[str]]] = []

    for subject, topics in syllabus.items():

        if isinstance(topics, list):
            for topic in topics:
                nodes.append(
                    {
                        "subject": str(subject),
                        "topic": str(topic),
                        "subtopic": None,
                    }
                )

        elif isinstance(topics, dict):
            for topic, subtopics in topics.items():

                if isinstance(subtopics, list):
                    for subtopic in subtopics:
                        nodes.append(
                            {
                                "subject": str(subject),
                                "topic": str(topic),
                                "subtopic": str(subtopic),
                            }
                        )
                else:
                    nodes.append(
                        {
                            "subject": str(subject),
                            "topic": str(topic),
                            "subtopic": None,
                        }
                    )

    return nodes


def _assessment_config(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Read assessment configuration without assuming a specific exam."""

    assessment = profile.get("assessment", {})

    if not isinstance(assessment, dict):
        return {}

    return assessment


def _configured_question_count(
    profile: Dict[str, Any],
) -> Optional[int]:

    assessment = _assessment_config(profile)

    count = assessment.get("question_count")

    if isinstance(count, int) and count > 0:
        return count

    return None


def _configured_duration(
    profile: Dict[str, Any],
) -> Optional[int]:

    assessment = _assessment_config(profile)

    duration = assessment.get("duration_minutes")

    if isinstance(duration, int) and duration > 0:
        return duration

    return None


def build_assessment_plan(
    profile: Dict[str, Any],
    mode: str = "targeted",
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    requested_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build an exam-aware assessment plan.

    Important distinction:

    targeted / weak_topic:
        Uses a small adaptive set.

    subject_test:
        Uses the exam's configured section information where available.

    full_mock:
        Uses the current versioned exam configuration.

    No exam-specific question count is embedded in this function.
    """

    profile = validate_exam_profile(profile)

    mode = str(mode or "targeted").strip().lower()

    if mode not in SUPPORTED_MODES:
        raise ValueError(
            "Invalid assessment mode. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_MODES))}"
        )

    assessment = _assessment_config(profile)

    configured_count = _configured_question_count(profile)

    # Adaptive practice intentionally stays small.
    if mode in {"targeted", "weak_topic"}:

        question_count = (
            int(requested_count)
            if requested_count and requested_count > 0
            else int(assessment.get("targeted_question_count", 10))
        )

    elif mode == "subject_test":

        subject_counts = assessment.get("subject_question_counts", {})

        if (
            subject
            and isinstance(subject_counts, dict)
            and isinstance(subject_counts.get(subject), int)
        ):
            question_count = subject_counts[subject]

        elif configured_count:
            subjects = profile.get("subjects") or []

            question_count = max(
                1,
                round(
                    configured_count /
                    max(1, len(subjects))
                ),
            )

        else:
            question_count = int(
                assessment.get("subject_test_question_count", 25)
            )

    else:
        # Full mock must follow the versioned exam profile.
        if configured_count is None:
            raise ValueError(
                f"No current full-mock question count is configured "
                f"for {profile['name']} version {profile['version']}."
            )

        question_count = configured_count

    syllabus_nodes = flatten_syllabus(profile)

    if subject:
        syllabus_nodes = [
            node
            for node in syllabus_nodes
            if node["subject"] == subject
        ]

    if topic:
        syllabus_nodes = [
            node
            for node in syllabus_nodes
            if node["topic"] == topic
        ]

    return {
        "exam": profile["name"],
        "exam_id": profile["id"],
        "syllabus_version": profile["version"],
        "mode": mode,
        "question_count": question_count,
        "duration_minutes": _configured_duration(profile),
        "subjects": deepcopy(profile.get("subjects", [])),
        "selected_subject": subject,
        "selected_topic": topic,
        "syllabus_nodes": syllabus_nodes,
        "marking_scheme": deepcopy(
            assessment.get("marking_scheme", {})
        ),
        "question_distribution": deepcopy(
            assessment.get("question_distribution", {})
        ),
        "source": deepcopy(profile.get("sources", [])),
    }


def build_learner_exam_profile(
    profile: Dict[str, Any],
    exam_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create the learner-facing exam profile.

    Exam data remains versioned so a syllabus update can create
    a new profile version without destroying historical attempts.
    """

    profile = validate_exam_profile(profile)

    parsed_date = None

    if exam_date:
        try:
            parsed_date = date.fromisoformat(exam_date).isoformat()
        except ValueError:
            raise ValueError(
                "exam_date must use YYYY-MM-DD format."
            )

    return {
        "exam_id": profile["id"],
        "exam_name": profile["name"],
        "syllabus_version": profile["version"],
        "exam_date": parsed_date,
        "subjects": deepcopy(profile.get("subjects", [])),
        "assessment": deepcopy(profile.get("assessment", {})),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def compare_syllabus_versions(
    old_profile: Dict[str, Any],
    new_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Detect syllabus changes between two official versions.

    This allows PaperScope to say:
    - added topics
    - removed topics
    - changed topics
    - unchanged competencies
    """

    old_nodes = {
        (
            node["subject"],
            node["topic"],
            node["subtopic"],
        )
        for node in flatten_syllabus(old_profile)
    }

    new_nodes = {
        (
            node["subject"],
            node["topic"],
            node["subtopic"],
        )
        for node in flatten_syllabus(new_profile)
    }

    added = sorted(new_nodes - old_nodes)
    removed = sorted(old_nodes - new_nodes)

    return {
        "old_version": str(old_profile.get("version", "")),
        "new_version": str(new_profile.get("version", "")),
        "added": [
            {
                "subject": item[0],
                "topic": item[1],
                "subtopic": item[2],
            }
            for item in added
        ],
        "removed": [
            {
                "subject": item[0],
                "topic": item[1],
                "subtopic": item[2],
            }
            for item in removed
        ],
        "changed": bool(added or removed),
    }
