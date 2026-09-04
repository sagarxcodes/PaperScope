from typing import Any, Dict, List


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def evaluate_competencies(
    questions: List[Dict[str, Any]],
    answers: List[Any],
) -> Dict[str, Any]:
    """
    Convert question-level performance into competency-level performance.

    Each question should contain:
      - competency
      - concept
      - answer

    answers contains the student's selected option index.
    """

    competency_stats: Dict[str, Dict[str, Any]] = {}

    for index, question in enumerate(questions):

        if index >= len(answers):
            break

        competency = str(
            question.get("competency")
            or question.get("concept")
            or "Unclassified Competency"
        ).strip()

        correct_answer = question.get("answer")

        try:
            student_answer = int(answers[index])
        except (TypeError, ValueError):
            student_answer = None

        correct = (
            student_answer is not None
            and correct_answer is not None
            and student_answer == correct_answer
        )

        if competency not in competency_stats:
            competency_stats[competency] = {
                "competency": competency,
                "questions": 0,
                "correct": 0,
                "incorrect": 0,
                "concepts": set(),
            }

        item = competency_stats[competency]

        item["questions"] += 1

        if correct:
            item["correct"] += 1
        else:
            item["incorrect"] += 1

        concept = question.get("concept")

        if concept:
            item["concepts"].add(str(concept))

    results = []

    for item in competency_stats.values():

        total = item["questions"]

        accuracy = (
            (item["correct"] / total) * 100
            if total
            else 0
        )

        accuracy = round(_clamp(accuracy), 2)

        if accuracy < 40:
            level = "critical_gap"
            priority = "high"
        elif accuracy < 60:
            level = "needs_improvement"
            priority = "high"
        elif accuracy < 75:
            level = "developing"
            priority = "medium"
        elif accuracy < 90:
            level = "proficient"
            priority = "low"
        else:
            level = "mastered"
            priority = "low"

        results.append({
            "competency": item["competency"],
            "questions": total,
            "correct": item["correct"],
            "incorrect": item["incorrect"],
            "accuracy": accuracy,
            "level": level,
            "priority": priority,
            "concepts": sorted(item["concepts"]),
        })

    results.sort(
        key=lambda x: (
            -(
                100 - x["accuracy"]
            ),
            -x["questions"],
        )
    )

    gaps = [
        item
        for item in results
        if item["accuracy"] < 75
    ]

    strengths = [
        item
        for item in results
        if item["accuracy"] >= 75
    ]

    return {
        "competencies": results,
        "gaps": gaps,
        "strengths": strengths,
        "total_competencies": len(results),
        "gap_count": len(gaps),
    }
