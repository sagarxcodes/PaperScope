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
from app.engines.question_intelligence_engine import (
    analyze_question_intelligence,
)
from app.engines.where_you_stand_engine import (
    build_where_you_stand,
)
from app.engines.calendar_engine import (
    build_ai_tasks,
    summarize_tasks,
)

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

    # ---------------------------------------------------------
    # QUESTION INTELLIGENCE
    # ---------------------------------------------------------
    # Analyze the uploaded material against PaperScope's
    # structured question bank and competency ontology.
    question_intelligence = analyze_question_intelligence(
        request.text,
        concepts=material.get("key_concepts", []),
        top_k=5,
    )

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
            retrieval_context=(
                question_intelligence
                .get("retrieval", {})
                .get("questions", [])
            ),
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

    # ---------------------------------------------------------
    # WHERE YOU STAND INTELLIGENCE
    # ---------------------------------------------------------
    # Convert the assessment into a learner-facing current
    # standing rather than treating the score as an isolated
    # assessment result.
    where_you_stand = build_where_you_stand(
        exam_name="PaperScope Assessment",
        current_score=overall_accuracy,
        maximum_score=100,
        topic_performance=topic_performance,
        target_score=80,
    )

    # ---------------------------------------------------------
    # SMART CALENDAR INTELLIGENCE
    # ---------------------------------------------------------
    # Feed the same competency gaps and Where You Stand result
    # into the calendar so recommendations become actionable.
    smart_calendar_tasks = build_ai_tasks(
        competency_gaps=competency.get(
            "competency_gaps",
            {},
        ),
        pyq_analysis={},
        where_you_stand=where_you_stand,
    )

    smart_calendar = {
        "tasks": smart_calendar_tasks,
        "summary": summarize_tasks(smart_calendar_tasks),
    }

    return {
        "success": True,
        "engine": "PaperScope Competency Intelligence Pipeline",
        "material": material,
        "question_intelligence": question_intelligence,
        "questions": questions,
        "assessment": assessment,
        "competency": competency,
        "adaptive_learning": adaptive,
        "personalized_recommendations": recommendations,
        "igot_training": training,

        # Integrated intelligence layer
        "where_you_stand": where_you_stand,
        "smart_calendar": smart_calendar,
    }
