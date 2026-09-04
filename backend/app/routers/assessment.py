from fastapi import APIRouter
from pydantic import BaseModel

from app.engines.assessment_engine import evaluate_assessment


router = APIRouter(
    prefix="/api/assessment",
    tags=["Assessment"],
)


class AssessmentRequest(BaseModel):
    questions: list
    answers: list


@router.post("/evaluate")
def evaluate(request: AssessmentRequest):

    return evaluate_assessment(
        request.questions,
        request.answers,
    )
