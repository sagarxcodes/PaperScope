def analyze_competency(topic_performance, overall_accuracy):
    competencies = []

    for topic, data in topic_performance.items():
        accuracy = float(data.get("accuracy", 0))
        questions = int(data.get("questions", 0))

        if accuracy >= 80:
            level = "strong"
            severity = "low"
            recommendation = f"Maintain your {topic} competency with advanced practice."

        elif accuracy >= 60:
            level = "developing"
            severity = "medium"
            recommendation = f"Practice more {topic} questions and review key concepts."

        else:
            level = "weak"
            severity = "high"
            recommendation = f"Prioritize {topic}. Review the learning material and complete targeted practice."

        competencies.append({
            "competency": topic,
            "accuracy": accuracy,
            "questions_assessed": questions,
            "level": level,
            "gap_severity": severity,
            "recommendation": recommendation,
        })

    competencies.sort(key=lambda x: x["accuracy"])

    strong = [
        item["competency"]
        for item in competencies
        if item["level"] == "strong"
    ]

    developing = [
        item["competency"]
        for item in competencies
        if item["level"] == "developing"
    ]

    weak = [
        item["competency"]
        for item in competencies
        if item["level"] == "weak"
    ]

    if overall_accuracy >= 80:
        readiness = "high"
    elif overall_accuracy >= 60:
        readiness = "moderate"
    else:
        readiness = "low"

    return {
        "success": True,
        "engine": "Competency Intelligence Engine",
        "overall_accuracy": round(float(overall_accuracy), 2),
        "readiness": readiness,
        "competency_count": len(competencies),
        "competencies": competencies,
        "strong_competencies": strong,
        "developing_competencies": developing,
        "competency_gaps": weak,
        "priority_gap": (
            weak[0]
            if weak
            else developing[0]
            if developing
            else None
        ),
    }
