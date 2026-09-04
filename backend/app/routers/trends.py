from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.engines.trend_engine import build_trend_analysis

router = APIRouter(
    prefix="/api/trends",
    tags=["Trend Intelligence"],
)


class TrendRequest(BaseModel):
    attempts: List[Dict[str, Any]] = Field(default_factory=list)
    exam_profile: Optional[Dict[str, Any]] = None
    target_accuracy: float = 80.0


@router.post("/analyze")
def analyze_trends(request: TrendRequest):
    result = build_trend_analysis(
        attempts=request.attempts,
        exam_profile=request.exam_profile,
        target_accuracy=request.target_accuracy,
    )

    return {
        "success": True,
        "engine": "PaperScope Trend Intelligence",
        "analysis": result,
    }
