from fastapi import APIRouter
from pydantic import BaseModel

from app.engines.material_engine import material_engine
from app.engines.question_engine import (
    generate_questions,
    build_concept_analysis,
)
from app.engines.assessment_engine import evaluate_assessment
from app.engines.competency_engine import analyze_competency
from app.engines.recommendation_engine import build_recommendations
from app.engines.training_engine import recommend_training
from app.engines.adaptive_engine import build_adaptive_plan

router = APIRouter(
    prefix="/api/pipeline",
    tags=["PaperScope Intelligence Pipeline"],
)

class PipelineRequest(BaseModel):
    text: str
    questions: list
    answers: list

@router.post("/analyze")
def analyze_pipeline(request: PipelineRequest):

    material = material_engine.analyze(request.text)

    if not material.get("success"):
        return material

    questions = request.questions or []

    if not questions:
        # Reuse the concept analysis already produced by
        # Material Intelligence instead of rediscovering
        # concepts independently.
        # Use Question Intelligence's clean educational
        # concept analysis instead of Material Intelligence's
        # raw keyword list.
        clean_concept_analysis = build_concept_analysis(
            request.text
        )

        question_analysis = dict(material)
        question_analysis["concept_analysis"] = (
            clean_concept_analysis
        )

        questions = generate_questions(
            request.text,
            number=10,
            analysis=question_analysis,
        )

    assessment = evaluate_assessment(
        questions,
        request.answers,
    )

    if not assessment.get("success"):
        topics = material.get("topics", [])

        topic_performance = {
            item["topic"]: {
                "questions": 0,
                "correct": 0,
                "accuracy": 0,
            }
            for item in topics
        }

        assessment = {
            "success": True,
            "total_questions": len(questions),
            "correct_answers": 0,
            "incorrect_answers": 0,
            "score": 0,
            "accuracy": 0,
            "readiness": "not_assessed",
            "topic_performance": topic_performance,
            "strengths": [],
            "developing_areas": [],
            "weaknesses": list(topic_performance.keys()),
            "results": [],
            "status": "baseline",
            "message": "Material analyzed. Complete the generated assessment for learner-specific competency scoring.",
        }

    topic_performance = assessment.get("topic_performance", {})
    overall_accuracy = assessment.get("accuracy", 0)

    competency = analyze_competency(
        topic_performance,
        overall_accuracy,
    )

    adaptive = build_adaptive_plan(
        topic_performance,
        overall_accuracy,
    )

    recommendations = build_recommendations(
        competency["competency_gaps"],
        topic_performance,
        overall_accuracy,
    )

    training = recommend_training(
        competency["competency_gaps"],
        overall_accuracy,
    )

    return {
        "success": True,
        "engine": "PaperScope Competency Intelligence Pipeline",
        "material": material,
        "questions": questions,
        "assessment": assessment,
        "competency": competency,
        "adaptive_learning": adaptive,
        "personalized_recommendations": recommendations,
        "igot_training": training,
    }
