from fastapi import APIRouter
from pydantic import BaseModel

from app.engines.competency_engine import analyze_competency


router = APIRouter(
    prefix="/api/competency",
    tags=["Competency Intelligence"],
)


class CompetencyRequest(BaseModel):
    topic_performance: dict
    overall_accuracy: float


@router.post("/analyze")
def competency_analysis(request: CompetencyRequest):

    return analyze_competency(
        request.topic_performance,
        request.overall_accuracy,
    )
