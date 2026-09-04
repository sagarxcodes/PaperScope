"""
PaperScope — Trend Intelligence Engine

Exam-agnostic performance analytics.
Works with any dynamically registered exam.
"""

from statistics import mean, pstdev
from typing import Any, Dict, List


def _accuracy(attempt: Dict[str, Any]) -> float:
    if "accuracy" in attempt:
        return float(attempt["accuracy"])

    questions = int(attempt.get("questions", 0) or 0)
    correct = int(attempt.get("correct", 0) or 0)

    if questions <= 0:
        return 0.0

    return round((correct / questions) * 100, 2)


def _mastery(attempt: Dict[str, Any], key: str) -> float:
    value = attempt.get(key)

    if value is None:
        return 0.0

    return float(value)


def _group_accuracy(
    attempts: List[Dict[str, Any]],
    field: str,
) -> List[Dict[str, Any]]:

    groups: Dict[str, List[float]] = {}

    for attempt in attempts:
        value = attempt.get(field)

        if not value:
            continue

        groups.setdefault(str(value), []).append(
            _accuracy(attempt)
        )

    result = []

    for name, values in groups.items():
        result.append({
            field: name,
            "attempts": len(values),
            "accuracy": round(mean(values), 2),
            "best": round(max(values), 2),
            "lowest": round(min(values), 2),
        })

    result.sort(
        key=lambda x: x["accuracy"],
        reverse=True,
    )

    return result


def _trend(values: List[float]) -> str:
    if len(values) < 2:
        return "insufficient_data"

    midpoint = max(1, len(values) // 2)

    first = mean(values[:midpoint])
    recent = mean(values[midpoint:])

    difference = recent - first

    if difference >= 8:
        return "strongly_improving"

    if difference >= 3:
        return "improving"

    if difference <= -8:
        return "declining"

    if difference <= -3:
        return "declining"

    return "stable"


def _velocity(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0

    return round(
        (values[-1] - values[0]) / (len(values) - 1),
        2,
    )


def _consistency(values: List[float]) -> float:
    if len(values) < 2:
        return 100.0

    deviation = pstdev(values)

    return round(
        max(0.0, min(100.0, 100.0 - deviation * 2)),
        2,
    )


def build_trend_analysis(
    attempts: List[Dict[str, Any]],
    exam_profile: Dict[str, Any] = None,
    target_accuracy: float = 80.0,
) -> Dict[str, Any]:

    if not attempts:
        return {
            "status": "insufficient_data",
            "attempt_count": 0,
            "message": (
                "Complete more assessments to generate "
                "a meaningful performance trend."
            ),
            "accuracy_trend": [],
            "mastery_trend": [],
            "subject_trends": [],
            "topic_trends": [],
            "insights": [],
            "next_action": "Complete a targeted assessment.",
        }

    # Preserve chronological order when timestamps are supplied.
    attempts = sorted(
        attempts,
        key=lambda x: str(
            x.get("timestamp", "")
        ),
    )

    accuracy_values = [
        _accuracy(attempt)
        for attempt in attempts
    ]

    accuracy_trend = []

    for index, attempt in enumerate(attempts, start=1):
        accuracy_trend.append({
            "attempt": index,
            "timestamp": attempt.get("timestamp"),
            "accuracy": _accuracy(attempt),
            "exam": attempt.get("exam"),
            "subject": attempt.get("subject"),
            "topic": attempt.get("topic"),
        })

    mastery_trend = []

    for index, attempt in enumerate(attempts, start=1):
        before = attempt.get("mastery_before")
        after = attempt.get("mastery_after")

        if before is not None or after is not None:
            mastery_trend.append({
                "attempt": index,
                "timestamp": attempt.get("timestamp"),
                "mastery_before": (
                    float(before) if before is not None else None
                ),
                "mastery_after": (
                    float(after) if after is not None else None
                ),
                "competency": attempt.get(
                    "competency",
                    attempt.get("topic"),
                ),
            })

    subject_trends = _group_accuracy(
        attempts,
        "subject",
    )

    topic_trends = _group_accuracy(
        attempts,
        "topic",
    )

    current_accuracy = round(
        accuracy_values[-1],
        2,
    )

    average_accuracy = round(
        mean(accuracy_values),
        2,
    )

    best_accuracy = round(
        max(accuracy_values),
        2,
    )

    velocity = _velocity(
        accuracy_values
    )

    consistency = _consistency(
        accuracy_values
    )

    direction = _trend(
        accuracy_values
    )

    gap = round(
        max(0.0, target_accuracy - current_accuracy),
        2,
    )

    insights = []

    if direction in {
        "improving",
        "strongly_improving",
    }:
        insights.append(
            "Your assessment accuracy is improving."
        )

    elif direction == "declining":
        insights.append(
            "Your recent accuracy is declining and needs intervention."
        )

    else:
        insights.append(
            "Your performance is relatively stable."
        )

    if gap > 0:
        insights.append(
            f"You are {gap:.1f} percentage points "
            f"below the current target."
        )
    else:
        insights.append(
            "You are currently meeting the target accuracy."
        )

    if subject_trends:
        weakest_subject = min(
            subject_trends,
            key=lambda x: x["accuracy"],
        )

        insights.append(
            f"{weakest_subject['subject']} is currently "
            f"your weakest subject at "
            f"{weakest_subject['accuracy']:.1f}% accuracy."
        )

    if topic_trends:
        weakest_topic = min(
            topic_trends,
            key=lambda x: x["accuracy"],
        )

        insights.append(
            f"{weakest_topic['topic']} is the largest "
            f"topic-level performance gap."
        )

    if direction == "declining":
        next_action = "Schedule intervention practice on the weakest competency."

    elif gap > 15:
        next_action = "Prioritize weak competencies before increasing difficulty."

    elif gap > 0:
        next_action = "Continue targeted practice and monitor the trend."

    else:
        next_action = "Progress toward higher difficulty and full mocks."

    exam_name = None

    if exam_profile:
        exam_name = (
            exam_profile.get("name")
            or exam_profile.get("exam")
        )

    return {
        "status": "ready",
        "exam": exam_name,
        "attempt_count": len(attempts),
        "current_accuracy": current_accuracy,
        "average_accuracy": average_accuracy,
        "best_accuracy": best_accuracy,
        "target_accuracy": target_accuracy,
        "gap_to_target": gap,
        "improvement_velocity": velocity,
        "consistency_score": consistency,
        "direction": direction,
        "accuracy_trend": accuracy_trend,
        "mastery_trend": mastery_trend,
        "subject_trends": subject_trends,
        "topic_trends": topic_trends,
        "insights": insights,
        "next_action": next_action,
    }
