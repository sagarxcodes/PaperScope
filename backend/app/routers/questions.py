from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.engines.question_engine import (
    generate_questions_from_analysis,
    generate_personalized_quiz,
)
from app.engines.assessment_engine import (
    evaluate_assessment,
)

from app.engines.adaptive_engine import (
    build_adaptive_plan,
)

from app.engines.where_you_stand_engine import (
    build_where_you_stand,
)

from app.engines.calendar_engine import (
    build_ai_tasks,
    summarize_tasks,
)


router = APIRouter(
    prefix="/api/questions",
    tags=["Question Generation"],
)


# ============================================================
# STANDARD QUESTION GENERATION
# ============================================================

class QuestionGenerationRequest(BaseModel):
    text: str
    number: int = 10


@router.post("/generate")
def generate_questions(
    request: QuestionGenerationRequest
):
    if not request.text.strip():
        return {
            "success": False,
            "message": "No learning material text supplied.",
            "questions": [],
        }

    number = max(1, min(request.number, 100))

    result = generate_questions_from_analysis(
        None,
        request.text,
        number,
    )

    return {
        "success": True,
        "questions": result,
        "count": len(result),
    }


# ============================================================
# PERSONALIZED QUIZ
# ============================================================

class PersonalizedQuizRequest(BaseModel):
    text: str
    number: int = Field(default=10, ge=1, le=50)

    learner_profile: Dict[str, Any] = Field(
        default_factory=dict
    )

    analysis: Optional[Dict[str, Any]] = None

    retrieval_context: Optional[List[Dict[str, Any]]] = None


@router.post("/personalized")
def generate_personalized_questions(
    request: PersonalizedQuizRequest
):
    """
    Generate an adaptive PaperScope quiz.

    The learner profile can contain:
      - exam_target
      - mastery
      - difficulty
      - recent_questions
      - PYQ performance
      - syllabus context

    Weak competencies are prioritized by the question engine.
    """

    if not request.text.strip():
        return {
            "success": False,
            "message": "No learning material text supplied.",
            "questions": [],
            "count": 0,
        }

    questions = generate_personalized_quiz(
        request.text,
        learner_profile=request.learner_profile,
        number=request.number,
        analysis=request.analysis,
        retrieval_context=request.retrieval_context,
    )

    return {
        "success": True,
        "mode": "PERSONALIZED",
        "questions": questions,
        "count": len(questions),
        "learner_profile": request.learner_profile,
    }


# ============================================================
# PERSONALIZED QUIZ SUBMISSION
# ============================================================

class PersonalizedAssessmentRequest(BaseModel):
    questions: List[Dict[str, Any]]
    answers: List[Any]

    learner_profile: Dict[str, Any] = Field(
        default_factory=dict
    )


@router.post("/personalized/submit")
def submit_personalized_quiz(
    request: PersonalizedAssessmentRequest
):
    """
    Evaluate a personalized quiz and update competency mastery.
    """

    if not request.questions:
        return {
            "success": False,
            "message": "No questions supplied.",
        }

    result = evaluate_assessment(
        request.questions,
        request.answers,
        learner_profile=request.learner_profile,
    )

    if not result.get("success"):
        return result

    # ========================================================
    # FULL ADAPTIVE INTELLIGENCE LOOP
    # ========================================================

    updated_mastery = result.get(
        "updated_mastery",
        {},
    )

    competency_performance = result.get(
        "competency_performance",
        {},
    )

    accuracy = float(
        result.get("accuracy", 0) or 0
    )

    # --------------------------------------------------------
    # 1. Build topic performance for adaptive intelligence.
    # --------------------------------------------------------

    topic_performance = {}

    for competency, data in competency_performance.items():
        if not isinstance(data, dict):
            continue

        topic_performance[competency] = {
            "accuracy": float(
                data.get("accuracy", 0) or 0
            ),
            "questions": int(
                data.get("questions", 0) or 0
            ),
            "correct": int(
                data.get("correct", 0) or 0
            ),
            "incorrect": int(
                data.get("incorrect", 0) or 0
            ),
        }

    # --------------------------------------------------------
    # 2. Adaptive learning plan.
    # --------------------------------------------------------

    adaptive = build_adaptive_plan(
        topic_performance,
        accuracy,
    )

    # --------------------------------------------------------
    # 3. Recompute learner standing after the quiz.
    # --------------------------------------------------------

    where_you_stand = build_where_you_stand(
        exam_name=request.learner_profile.get(
            "exam_target",
            "PaperScope Assessment",
        ),
        current_score=accuracy,
        maximum_score=100,
        topic_performance=topic_performance,
        target_score=80,
    )

    # --------------------------------------------------------
    # 4. Generate concrete calendar actions from the
    #    NEW mastery state.
    # --------------------------------------------------------

    smart_calendar_tasks = build_ai_tasks(
        competency_gaps={},
        pyq_analysis={},
        where_you_stand=where_you_stand,
    )

    smart_calendar = {
        "tasks": smart_calendar_tasks,
        "summary": summarize_tasks(
            smart_calendar_tasks
        ),
    }

    # --------------------------------------------------------
    # 5. Return the complete adaptive state.
    # --------------------------------------------------------

    return {
        "success": True,
        "mode": "PERSONALIZED_ASSESSMENT",

        "score": result.get("score"),
        "accuracy": accuracy,
        "readiness": result.get("readiness"),

        "competency_performance": competency_performance,

        "updated_mastery": updated_mastery,

        "strengths": result.get(
            "strengths",
            [],
        ),

        "developing_areas": result.get(
            "developing_areas",
            [],
        ),

        "weaknesses": result.get(
            "weaknesses",
            [],
        ),

        # The next competency to attack.
        "next_adaptive_target": result.get(
            "next_adaptive_target"
        ),

        # Full adaptive learning plan.
        "adaptive_learning": adaptive,

        # Updated learner standing.
        "where_you_stand": where_you_stand,

        # Concrete actions generated from the updated state.
        "smart_calendar": smart_calendar,

        "results": result.get(
            "results",
            [],
        ),
    }
