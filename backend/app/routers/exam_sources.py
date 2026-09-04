from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.engines.exam_source_engine import (
    get_source,
    list_versions,
    compare_with_latest,
    register_versioned_profile,
)

router = APIRouter(
    prefix="/api/exam-sources",
    tags=["Exam Sources"],
)


class RegisterExamVersionRequest(BaseModel):
    profile: Dict[str, Any]
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_exam_sources():
    from app.engines.exam_source_engine import load_sources

    data = load_sources()

    return {
        "success": True,
        "sources": data.get("sources", []),
        "count": len(data.get("sources", [])),
        "engine": "PaperScope Official Exam Source Intelligence",
    }


@router.get("/{exam_id}")
def exam_source(exam_id: str):
    source = get_source(exam_id)

    if not source:
        raise HTTPException(
            status_code=404,
            detail=f"No official source registered for {exam_id}",
        )

    return {
        "success": True,
        "source": source,
        "versions": list_versions(exam_id),
        "engine": "PaperScope Official Exam Source Intelligence",
    }


@router.post("/compare")
def compare_exam_version(request: RegisterExamVersionRequest):
    try:
        result = compare_with_latest(request.profile)

        return {
            "success": True,
            "comparison": result,
            "engine": "PaperScope Official Exam Source Intelligence",
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/register")
def register_exam_version(request: RegisterExamVersionRequest):
    try:
        result = register_versioned_profile(
            request.profile,
            request.source_metadata,
        )

        return {
            "success": True,
            "registration": result,
            "engine": "PaperScope Official Exam Source Intelligence",
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
