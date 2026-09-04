TRAINING_CATALOG = [
    {
        "id": "IGOT-STAT-001",
        "title": "Fundamentals of Statistical Methods",
        "competencies": ["Statistical Methods", "Data Analysis"],
        "level": "beginner",
        "duration": "2 hours",
        "provider": "iGOT Karmayogi",
    },
    {
        "id": "IGOT-PROB-001",
        "title": "Probability and Statistical Reasoning",
        "competencies": ["Probability"],
        "level": "beginner",
        "duration": "2.5 hours",
        "provider": "iGOT Karmayogi",
    },
    {
        "id": "IGOT-SURVEY-001",
        "title": "Survey Methodology",
        "competencies": ["Survey Methodology", "Research Methods"],
        "level": "intermediate",
        "duration": "3 hours",
        "provider": "iGOT Karmayogi",
    },
    {
        "id": "IGOT-DATA-001",
        "title": "Data Analysis for Official Statistics",
        "competencies": ["Data Analysis", "Statistical Methods"],
        "level": "intermediate",
        "duration": "3 hours",
        "provider": "iGOT Karmayogi",
    },
]


def recommend_training(
    competency_gaps,
    overall_accuracy,
):
    recommendations = []

    for gap in competency_gaps:

        matches = []

        for course in TRAINING_CATALOG:
            if gap.lower() in [
                competency.lower()
                for competency in course["competencies"]
            ]:
                matches.append(course)

        recommendations.append({
            "competency_gap": gap,
            "recommended_courses": matches,
            "course_count": len(matches),
        })

    if overall_accuracy < 60:
        learning_level = "foundation"
    elif overall_accuracy < 80:
        learning_level = "intermediate"
    else:
        learning_level = "advanced"

    return {
        "success": True,
        "engine": "iGOT Training Recommendation Engine",
        "learning_level": learning_level,
        "gap_count": len(competency_gaps),
        "recommendations": recommendations,
    }
