from fastapi import APIRouter
from pydantic import BaseModel

from app.engines.training_engine import recommend_training


router = APIRouter(
    prefix="/api/training",
    tags=["iGOT Training"],
)


class TrainingRequest(BaseModel):
    competency_gaps: list
    overall_accuracy: float


@router.post("/recommend")
def training_recommendation(request: TrainingRequest):

    return recommend_training(
        request.competency_gaps,
        request.overall_accuracy,
    )
