from fastapi import APIRouter
from pydantic import BaseModel

from app.engines.recommendation_engine import build_recommendations


router = APIRouter(
    prefix="/api/recommendation",
    tags=["Recommendation Intelligence"],
)


class RecommendationRequest(BaseModel):
    competency_gaps: list
    topic_performance: dict
    overall_accuracy: float


@router.post("/generate")
def generate_recommendations(request: RecommendationRequest):

    return build_recommendations(
        request.competency_gaps,
        request.topic_performance,
        request.overall_accuracy,
    )
