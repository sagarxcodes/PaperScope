"""
PaperScope - Where You Stand Intelligence Engine V1

Purpose:
Evaluate a learner's current academic standing, identify improvement
requirements, and project a realistic outcome from measurable progress.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def _level(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "strong"
    if score >= 50:
        return "developing"
    if score >= 30:
        return "needs_improvement"
    return "critical"


def _standing(score: float) -> str:
    if score >= 90:
        return "top_range"
    if score >= 75:
        return "competitive"
    if score >= 60:
        return "progressing"
    if score >= 40:
        return "developing"
    return "foundation"


def _priority(gap: float) -> str:
    if gap >= 30:
        return "must_study"
    if gap >= 15:
        return "high"
    if gap >= 7:
        return "medium"
    return "low"


def _normalise_topic_scores(
    topic_performance: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    results = []

    if not isinstance(topic_performance, dict):
        return results

    for topic, data in topic_performance.items():
        if not isinstance(data, dict):
            continue

        accuracy = data.get("accuracy", data.get("score", 0))

        try:
            accuracy = float(accuracy)
        except (TypeError, ValueError):
            accuracy = 0

        accuracy = _clamp(accuracy)

        results.append(
            {
                "topic": str(topic),
                "accuracy": round(accuracy, 1),
                "questions": int(data.get("questions", 0) or 0),
                "correct": int(data.get("correct", 0) or 0),
                "gap": round(max(0, 80 - accuracy), 1),
                "priority": _priority(max(0, 80 - accuracy)),
                "level": _level(accuracy),
            }
        )

    return sorted(
        results,
        key=lambda item: (-item["gap"], item["topic"].lower()),
    )


def _project_score(
    current_score: float,
    improvement_points: float,
) -> float:
    """
    Project a future score from an explicit improvement assumption.

    This is intentionally transparent rather than pretending to predict
    an exact future result.
    """
    return round(_clamp(current_score + improvement_points), 1)


def build_where_you_stand(
    *,
    exam_name: str = "General Assessment",
    current_score: float = 0,
    maximum_score: float = 100,
    topic_performance: Optional[Dict[str, Any]] = None,
    target_score: Optional[float] = None,
    historical_cutoff: Optional[float] = None,
    current_percentile: Optional[float] = None,
    historical_rank: Optional[int] = None,
) -> Dict[str, Any]:

    try:
        current_score = float(current_score)
        maximum_score = float(maximum_score)
    except (TypeError, ValueError):
        current_score = 0
        maximum_score = 100

    maximum_score = max(1, maximum_score)
    current_score = max(0, min(current_score, maximum_score))

    current_percentage = round(
        (current_score / maximum_score) * 100,
        1,
    )

    topic_scores = _normalise_topic_scores(topic_performance)

    if target_score is None:
        target_score = maximum_score * 0.80

    try:
        target_score = float(target_score)
    except (TypeError, ValueError):
        target_score = maximum_score * 0.80

    target_score = max(0, min(target_score, maximum_score))

    target_percentage = round(
        (target_score / maximum_score) * 100,
        1,
    )

    improvement_needed = round(
        max(0, target_score - current_score),
        1,
    )

    improvement_percentage_points = round(
        max(0, target_percentage - current_percentage),
        1,
    )

    # Transparent improvement scenarios.
    projections = []

    for label, improvement in [
        ("Current trajectory", 0),
        ("Moderate improvement", improvement_needed * 0.50),
        ("Strong improvement", improvement_needed * 0.75),
        ("Target achieved", improvement_needed),
    ]:
        projected_score = _project_score(
            current_score,
            improvement,
        )

        projected_percentage = round(
            (projected_score / maximum_score) * 100,
            1,
        )

        projections.append(
            {
                "scenario": label,
                "score": projected_score,
                "percentage": projected_percentage,
            }
        )

    # Cutoff comparison when historical data is supplied.
    cutoff_analysis = None

    if historical_cutoff is not None:
        try:
            historical_cutoff = float(historical_cutoff)

            difference = round(
                current_score - historical_cutoff,
                1,
            )

            if difference >= 10:
                status = "above_cutoff"
            elif difference >= 0:
                status = "near_cutoff"
            else:
                status = "below_cutoff"

            cutoff_analysis = {
                "historical_cutoff": historical_cutoff,
                "difference": difference,
                "status": status,
                "message": (
                    "Current score is above the supplied historical cutoff."
                    if status == "above_cutoff"
                    else
                    "Current score is close to the supplied historical cutoff."
                    if status == "near_cutoff"
                    else
                    "Current score is below the supplied historical cutoff."
                ),
            }
        except (TypeError, ValueError):
            cutoff_analysis = None

    strongest_topics = sorted(
        topic_scores,
        key=lambda item: item["accuracy"],
        reverse=True,
    )[:3]

    priority_topics = [
        item for item in topic_scores
        if item["gap"] > 0
    ][:5]

    improvement_topics = [
        item for item in topic_scores
        if item["accuracy"] < 80
    ]

    return {
        "success": True,
        "engine": "PaperScope Where You Stand Intelligence V1",
        "exam": {
            "name": exam_name,
            "maximum_score": maximum_score,
        },
        "current_standing": {
            "score": round(current_score, 1),
            "percentage": current_percentage,
            "level": _level(current_percentage),
            "standing": _standing(current_percentage),
            "percentile": current_percentile,
            "historical_rank": historical_rank,
        },
        "target_analysis": {
            "target_score": round(target_score, 1),
            "target_percentage": target_percentage,
            "improvement_needed": improvement_needed,
            "improvement_percentage_points": improvement_percentage_points,
            "target_status": (
                "achieved"
                if current_score >= target_score
                else "in_progress"
            ),
        },
        "topic_analysis": {
            "all_topics": topic_scores,
            "priority_topics": priority_topics,
            "strongest_topics": strongest_topics,
        },
        "cutoff_analysis": cutoff_analysis,
        "projections": projections,
        "action_plan": [
            {
                "action": "Fix highest-gap topics",
                "reason": (
                    "These topics currently contribute the largest "
                    "performance gaps."
                ),
                "topics": [
                    item["topic"]
                    for item in improvement_topics[:3]
                ],
            },
            {
                "action": "Practice targeted questions",
                "reason": (
                    "Use topic-focused practice to convert weak areas "
                    "into measurable score improvement."
                ),
            },
            {
                "action": "Reassess after improvement",
                "reason": (
                    "A new assessment should update the learner's "
                    "current standing."
                ),
            },
        ],
        "summary": {
            "message": (
                f"You currently stand at {current_percentage}% "
                f"for {exam_name}. "
                f"{'Your target has been achieved.' if current_score >= target_score else f'{improvement_percentage_points} percentage points of improvement are needed to reach the current target.'}"
            ),
        },
    }
