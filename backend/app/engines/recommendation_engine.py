def build_recommendations(
    competency_gaps,
    topic_performance,
    overall_accuracy,
):
    recommendations = []

    for topic in competency_gaps:

        performance = topic_performance.get(topic, {})
        accuracy = float(performance.get("accuracy", 0))

        if accuracy < 40:
            priority = "critical"
            action = "Relearn fundamentals"
            study_time = "30-45 minutes"
        elif accuracy < 60:
            priority = "high"
            action = "Review concepts and practice targeted questions"
            study_time = "20-30 minutes"
        else:
            priority = "medium"
            action = "Target weak concepts and practice more questions"
            study_time = "15-20 minutes"

        recommendations.append({
            "topic": topic,
            "priority": priority,
            "accuracy": round(accuracy, 2),
            "action": action,
            "study_time": study_time,
            "recommended_content": [
                f"{topic} fundamentals",
                f"{topic} worked examples",
                f"{topic} practice questions",
            ],
            "reason": (
                f"Your accuracy in {topic} is "
                f"{round(accuracy, 2)}%, indicating a competency gap."
            ),
        })

    if overall_accuracy >= 80:
        learning_strategy = "Advanced progression"
    elif overall_accuracy >= 60:
        learning_strategy = "Targeted improvement"
    else:
        learning_strategy = "Foundation rebuilding"

    return {
        "success": True,
        "engine": "Recommendation Intelligence Engine",
        "overall_accuracy": round(float(overall_accuracy), 2),
        "learning_strategy": learning_strategy,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
    }
