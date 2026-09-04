from collections import defaultdict


def _safe_float(value, default=50.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_competency(question):
    """
    Resolve the most specific competency attached to a question.
    Personalized questions use target_competency/competency.
    Older questions can still use topic/concept.
    """

    competency = (
        question.get("target_competency")
        or question.get("competency")
        or question.get("topic")
        or question.get("concept")
        or "General"
    )

    if isinstance(competency, dict):
        competency = (
            competency.get("topic")
            or competency.get("name")
            or competency.get("concept")
            or "General"
        )

    if not isinstance(competency, str) or not competency.strip():
        return "General"

    return competency.strip()


def _updated_mastery(old_mastery, accuracy, question_count):
    """
    Conservative mastery update.

    The quiz result should influence mastery, but one small quiz
    should not completely overwrite the learner's previous profile.

    More questions = slightly stronger update.
    """

    old_mastery = _safe_float(old_mastery, 50.0)
    accuracy = _safe_float(accuracy, 0.0)

    # Learning rate grows modestly with evidence.
    learning_rate = min(
        0.35,
        0.15 + (max(question_count, 1) - 1) * 0.04
    )

    updated = (
        old_mastery * (1.0 - learning_rate)
        + accuracy * learning_rate
    )

    return round(max(0.0, min(100.0, updated)), 1)


def evaluate_assessment(
    questions,
    answers,
    learner_profile=None,
):
    """
    Evaluate a quiz and produce competency-level mastery updates.

    Backward compatible:
        evaluate_assessment(questions, answers)

    Personalized mode:
        evaluate_assessment(
            questions,
            answers,
            learner_profile
        )
    """

    learner_profile = learner_profile or {}

    total = len(questions)

    if total == 0:
        return {
            "success": False,
            "message": "No questions supplied.",
        }

    correct = 0

    competency_stats = defaultdict(
        lambda: {
            "total": 0,
            "correct": 0,
            "mastery_before": None,
        }
    )

    results = []

    for index, question in enumerate(questions):

        user_answer = (
            answers[index]
            if index < len(answers)
            else None
        )

        correct_answer = question.get("answer")

        # Exact answer matching preserves the existing behaviour.
        is_correct = user_answer == correct_answer

        if is_correct:
            correct += 1

        competency = _get_competency(question)

        stats = competency_stats[competency]

        stats["total"] += 1

        if is_correct:
            stats["correct"] += 1

        # Prefer the mastery captured when this personalized
        # question was generated.
        if stats["mastery_before"] is None:
            if question.get("mastery_before") is not None:
                stats["mastery_before"] = _safe_float(
                    question.get("mastery_before")
                )

        results.append({
            "question_id": question.get("id"),
            "topic": competency,
            "competency": competency,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "correct": is_correct,
            "question_type": question.get(
                "question_type",
                "standard",
            ),
            "difficulty": question.get(
                "difficulty",
                question.get(
                    "personalization",
                    {}
                ).get(
                    "recommended_difficulty",
                    "medium",
                ),
            ),
        })

    accuracy = round(
        (correct / total) * 100,
        1,
    )

    # --------------------------------------------------------
    # COMPETENCY PERFORMANCE
    # --------------------------------------------------------

    competency_performance = {}

    for competency, stats in competency_stats.items():

        competency_accuracy = round(
            (
                stats["correct"]
                / stats["total"]
            ) * 100,
            1,
        )

        mastery_before = stats["mastery_before"]

        # If the question didn't carry a mastery value,
        # recover it from the supplied learner profile.
        if mastery_before is None:

            mastery_map = (
                learner_profile.get("mastery", {})
                or {}
            )

            mastery_before = _safe_float(
                mastery_map.get(competency, 50.0),
                50.0,
            )

        mastery_after = _updated_mastery(
            mastery_before,
            competency_accuracy,
            stats["total"],
        )

        competency_performance[competency] = {
            "questions": stats["total"],
            "correct": stats["correct"],
            "accuracy": competency_accuracy,
            "mastery_before": round(
                mastery_before,
                1,
            ),
            "mastery_after": mastery_after,
            "mastery_change": round(
                mastery_after - mastery_before,
                1,
            ),
        }

    # --------------------------------------------------------
    # GLOBAL CATEGORIES
    # --------------------------------------------------------

    strengths = [
        competency
        for competency, data
        in competency_performance.items()
        if data["accuracy"] >= 70
    ]

    weaknesses = [
        competency
        for competency, data
        in competency_performance.items()
        if data["accuracy"] < 50
    ]

    developing = [
        competency
        for competency, data
        in competency_performance.items()
        if 50 <= data["accuracy"] < 70
    ]

    # --------------------------------------------------------
    # UPDATED MASTERY PROFILE
    # --------------------------------------------------------

    updated_mastery = {}

    existing_mastery = (
        learner_profile.get("mastery", {})
        or {}
    )

    # Preserve competencies that were not tested.
    for competency, value in existing_mastery.items():
        updated_mastery[competency] = round(
            _safe_float(value),
            1,
        )

    # Replace tested competencies with their updated mastery.
    for competency, data in competency_performance.items():
        updated_mastery[competency] = data[
            "mastery_after"
        ]

    # --------------------------------------------------------
    # NEXT ADAPTIVE TARGET
    # --------------------------------------------------------

    ranked_targets = sorted(
        competency_performance.items(),
        key=lambda item: (
            item[1]["mastery_after"],
            item[1]["accuracy"],
        ),
    )

    next_target = None

    if ranked_targets:
        competency, data = ranked_targets[0]

        next_target = {
            "competency": competency,
            "mastery": data["mastery_after"],
            "accuracy": data["accuracy"],
            "reason": (
                "Lowest post-assessment mastery; "
                "prioritize targeted practice."
            ),
        }

    # --------------------------------------------------------
    # READINESS
    # --------------------------------------------------------

    if accuracy >= 80:
        readiness = "high"
    elif accuracy >= 60:
        readiness = "moderate"
    else:
        readiness = "developing"

    return {
        "success": True,

        "total_questions": total,
        "correct_answers": correct,
        "incorrect_answers": total - correct,
        "score": correct,
        "accuracy": accuracy,
        "readiness": readiness,

        # Backward-compatible field.
        "topic_performance": competency_performance,

        # New SIH competency intelligence.
        "competency_performance": competency_performance,
        "updated_mastery": updated_mastery,

        "strengths": strengths,
        "developing_areas": developing,
        "weaknesses": weaknesses,

        "next_adaptive_target": next_target,

        "results": results,
    }
