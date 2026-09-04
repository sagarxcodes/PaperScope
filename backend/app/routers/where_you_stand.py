from typing import Optional

from fastapi import APIRouter

from app.engines.where_you_stand_engine import build_where_you_stand

router = APIRouter(
    prefix="/api/where-you-stand",
    tags=["Where You Stand"],
)


@router.post("/analyze")
def analyze_where_you_stand(payload: dict):
    return build_where_you_stand(
        exam_name=payload.get(
            "exam_name",
            "General Assessment",
        ),
        current_score=payload.get(
            "current_score",
            0,
        ),
        maximum_score=payload.get(
            "maximum_score",
            100,
        ),
        topic_performance=payload.get(
            "topic_performance",
            {},
        ),
        target_score=payload.get(
            "target_score",
        ),
        historical_cutoff=payload.get(
            "historical_cutoff",
        ),
        current_percentile=payload.get(
            "current_percentile",
        ),
        historical_rank=payload.get(
            "historical_rank",
        ),
    )


@router.post("/from-analysis")
def where_you_stand_from_analysis(payload: dict):
    assessment = payload.get("assessment", {}) or {}
    competency = payload.get("competency", {}) or {}

    topic_performance = assessment.get(
        "topic_performance",
        {},
    )

    accuracy = assessment.get(
        "accuracy",
        0,
    )

    maximum_score = payload.get(
        "maximum_score",
        100,
    )

    current_score = (
        float(accuracy) / 100
    ) * float(maximum_score)

    return build_where_you_stand(
        exam_name=payload.get(
            "exam_name",
            "PaperScope Assessment",
        ),
        current_score=current_score,
        maximum_score=maximum_score,
        topic_performance=topic_performance,
        target_score=payload.get(
            "target_score",
            float(maximum_score) * 0.80,
        ),
        historical_cutoff=payload.get(
            "historical_cutoff",
        ),
        current_percentile=payload.get(
            "current_percentile",
        ),
        historical_rank=payload.get(
            "historical_rank",
        ),
    )
