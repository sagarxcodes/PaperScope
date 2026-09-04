def build_adaptive_plan(topic_performance, overall_accuracy):
    priorities = []

    for topic, data in topic_performance.items():
        accuracy = float(data.get("accuracy", 0) or 0)
        questions = int(data.get("questions", data.get("total", 0)) or 0)
        correct = int(data.get("correct", 0) or 0)

        incorrect = data.get("incorrect")
        if incorrect is None:
            incorrect = max(0, questions - correct)
        incorrect = int(incorrect)

        repeated_wrong = int(
            data.get(
                "repeated_wrong",
                data.get("wrong_streak", 0)
            ) or 0
        )

        # Base weakness priority.
        if accuracy < 50:
            level = "high"
            action = "Intensive practice"
            next_difficulty = "easy"
            base_weight = 3
        elif accuracy < 70:
            level = "medium"
            action = "Targeted practice"
            next_difficulty = "medium"
            base_weight = 2
        else:
            level = "low"
            action = "Maintenance practice"
            next_difficulty = "hard"
            base_weight = 1

        # Repeated mistakes increase priority.
        repetition_bonus = min(repeated_wrong, 5)
        practice_weight = base_weight + repetition_bonus

        if repeated_wrong >= 3:
            action = "Repeated-error intervention"
            next_difficulty = "easy"
            level = "high"

        priorities.append({
            "topic": topic,
            "accuracy": round(accuracy, 1),
            "questions": questions,
            "correct": correct,
            "incorrect": incorrect,
            "repeated_wrong": repeated_wrong,
            "priority": level,
            "action": action,
            "next_difficulty": next_difficulty,
            "practice_weight": practice_weight,
        })

    priorities.sort(
        key=lambda item: (
            item["practice_weight"],
            item["incorrect"],
            -item["accuracy"],
        ),
        reverse=True,
    )

    if overall_accuracy < 50:
        learning_mode = "foundation"
    elif overall_accuracy < 70:
        learning_mode = "improvement"
    elif overall_accuracy < 85:
        learning_mode = "progression"
    else:
        learning_mode = "mastery"

    if priorities:
        focus_topic = priorities[0]["topic"]
        recommended_difficulty = priorities[0]["next_difficulty"]
    else:
        focus_topic = None
        recommended_difficulty = "medium"

    return {
        "success": True,
        "learning_mode": learning_mode,
        "overall_accuracy": round(float(overall_accuracy), 1),
        "focus_topic": focus_topic,
        "recommended_difficulty": recommended_difficulty,
        "topic_priorities": priorities,
    }
