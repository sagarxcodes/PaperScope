from typing import Any, Dict, List


def build_adaptive_question_plan(
    competency_result: Dict[str, Any],
    available_questions: List[Dict[str, Any]],
    questions_per_gap: int = 3,
) -> Dict[str, Any]:

    gaps = competency_result.get("gaps", [])

    plan = []

    for gap in gaps:

        competency = gap.get("competency", "")
        accuracy = float(gap.get("accuracy", 0))

        if accuracy < 40:
            target_difficulty = "easy"
            reason = "Build foundational understanding before increasing difficulty."
        elif accuracy < 60:
            target_difficulty = "medium"
            reason = "Reinforce the concept with targeted practice."
        else:
            target_difficulty = "hard"
            reason = "Challenge the learner to reach mastery."

        matching = [
            q for q in available_questions
            if competency.lower() in str(
                q.get("competency", "")
            ).lower()
        ]

        # Prefer the target difficulty.
        exact = [
            q for q in matching
            if str(q.get("difficulty", "")).lower()
            == target_difficulty
        ]

        selected = (exact or matching)[:questions_per_gap]

        plan.append({
            "competency": competency,
            "current_accuracy": accuracy,
            "priority": gap.get("priority"),
            "current_level": gap.get("level"),
            "target_difficulty": target_difficulty,
            "reason": reason,
            "recommended_questions": [
                {
                    "id": q.get("id"),
                    "question": q.get("question"),
                    "concept": q.get("concept"),
                    "difficulty": q.get("difficulty"),
                }
                for q in selected
            ],
        })

    return {
        "strategy": "competency_gap_driven",
        "total_gaps": len(gaps),
        "learning_plan": plan,
    }
