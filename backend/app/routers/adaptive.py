from fastapi import APIRouter
from pydantic import BaseModel

from app.engines.adaptive_engine import build_adaptive_plan


router = APIRouter(
    prefix="/api/adaptive",
    tags=["Adaptive Intelligence"],
)


class AdaptiveRequest(BaseModel):
    topic_performance: dict
    overall_accuracy: float


@router.post("/plan")
def adaptive_plan(request: AdaptiveRequest):

    return build_adaptive_plan(
        request.topic_performance,
        request.overall_accuracy,
    )
