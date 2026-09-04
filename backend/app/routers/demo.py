from fastapi import APIRouter

router = APIRouter(prefix="/api/demo", tags=["SIH Demo"])


@router.get("/analysis")
def demo_analysis():
    return {
        "mode": "DEMO",
        "material": {
            "title": "Introduction to Official Statistics",
            "type": "Lecture Notes",
            "subject": "Official Statistics",
            "pages": 8
        },
        "concepts": [
            "Official Statistics",
            "Statistical Systems",
            "Data Collection",
            "Data Quality",
            "Statistical Indicators"
        ],
        "competencies": [
            {"name": "Understanding Official Statistics", "score": 86, "level": "Strong"},
            {"name": "Data Collection & Sources", "score": 68, "level": "Developing"},
            {"name": "Data Quality Assessment", "score": 48, "level": "Needs Improvement"},
            {"name": "Statistical Interpretation", "score": 57, "level": "Developing"}
        ],
        "competency_gaps": [
            {
                "competency": "Data Quality Assessment",
                "score": 48,
                "gap": "High",
                "reason": "Limited understanding of validation, consistency and quality dimensions."
            },
            {
                "competency": "Statistical Interpretation",
                "score": 57,
                "gap": "Medium",
                "reason": "Needs improvement in interpreting statistical indicators."
            }
        ],
        "difficulty": {
            "easy": 35,
            "medium": 45,
            "hard": 20
        },
        "importance": [
            {"concept": "Data Quality", "importance": 92},
            {"concept": "Official Statistics", "importance": 88},
            {"concept": "Data Collection", "importance": 79}
        ],
        "recommendations": [
            "Complete a learning module on Data Quality Assessment.",
            "Practice questions involving validation and statistical consistency.",
            "Review statistical indicators and their interpretation."
        ],
        "training": [
            {
                "title": "Data Quality and Statistical Standards",
                "provider": "iGOT Karmayogi",
                "reason": "Targets the highest competency gap"
            },
            {
                "title": "Understanding Official Statistics",
                "provider": "iGOT Karmayogi",
                "reason": "Strengthens foundational knowledge"
            }
        ]
    }


@router.get("/quiz")
def demo_quiz():
    return {
        "mode": "DEMO",
        "title": "Official Statistics Competency Quiz",
        "questions": [
            {
                "id": 1,
                "question": "Which is an important characteristic of high-quality official statistics?",
                "options": ["Randomness", "Accuracy", "Complexity", "Subjectivity"],
                "answer": "Accuracy"
            },
            {
                "id": 2,
                "question": "Which activity is directly related to data quality assessment?",
                "options": ["Data validation", "Graphic design", "Advertising", "File compression"],
                "answer": "Data validation"
            },
            {
                "id": 3,
                "question": "Official statistics are primarily produced to describe:",
                "options": [
                    "Economic and social conditions",
                    "Only private companies",
                    "Only sports events",
                    "Only entertainment trends"
                ],
                "answer": "Economic and social conditions"
            },
            {
                "id": 4,
                "question": "Which competency is identified as the largest gap in this assessment?",
                "options": [
                    "Official Statistics",
                    "Data Collection",
                    "Data Quality Assessment",
                    "Basic Mathematics"
                ],
                "answer": "Data Quality Assessment"
            },
            {
                "id": 5,
                "question": "Why is statistical interpretation important?",
                "options": [
                    "To understand what statistical indicators mean",
                    "To increase file size",
                    "To remove datasets",
                    "To avoid data collection"
                ],
                "answer": "To understand what statistical indicators mean"
            }
        ]
    }


@router.get("/cases")
def demo_cases():
    return {
        "mode": "DEMO",
        "cases": [
            {
                "id": 1,
                "title": "Official Statistics Learning",
                "material": "Lecture notes",
                "gap": "Data Quality Assessment",
                "action": "Generate targeted MCQs",
                "recommendation": "Data Quality training"
            },
            {
                "id": 2,
                "title": "Competency Assessment",
                "material": "Training material",
                "gap": "Statistical Interpretation",
                "action": "Adaptive assessment",
                "recommendation": "Statistics interpretation module"
            },
            {
                "id": 3,
                "title": "Multi-Year Question Papers",
                "material": "2024, 2025 and 2026 papers",
                "gap": "Repeated weak concepts",
                "action": "Trend and weightage analysis",
                "recommendation": "Personalized revision plan"
            }
        ]
    }
