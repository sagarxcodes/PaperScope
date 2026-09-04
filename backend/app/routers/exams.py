from pathlib import Path
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.engines.exam_intelligence_engine import (
    build_assessment_plan,
    build_learner_exam_profile,
    compare_syllabus_versions,
    validate_exam_profile,
)

router = APIRouter(prefix="/api/exams", tags=["Exam Intelligence"])

EXAM_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "exams"


def _files():
    EXAM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(EXAM_DATA_DIR.glob("*.json"))


def _normalize(value: str) -> str:
    return str(value or "").strip().upper().replace("-", "_").replace(" ", "_")


def _load_profile(exam_id: str) -> Dict[str, Any]:
    wanted = _normalize(exam_id)
    matches = []

    for path in _files():
        try:
            data = json.loads(path.read_text())
            if _normalize(data.get("id")) == wanted:
                matches.append(data)
        except Exception:
            continue

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"Exam '{exam_id}' was not found in the registry.",
        )

    matches.sort(key=lambda x: str(x.get("version", "")))
    return validate_exam_profile(matches[-1])


class ExamProfileRequest(BaseModel):
    profile: Dict[str, Any]


class AssessmentPlanRequest(BaseModel):
    exam: str
    mode: str = "targeted"
    subject: Optional[str] = None
    topic: Optional[str] = None
    requested_count: Optional[int] = None


class LearnerExamRequest(BaseModel):
    exam: str
    exam_date: Optional[str] = None


class CompareVersionsRequest(BaseModel):
    old_profile: Dict[str, Any]
    new_profile: Dict[str, Any]


@router.get("")
def list_exams():
    exams = []

    for path in _files():
        try:
            profile = validate_exam_profile(json.loads(path.read_text()))
            exams.append({
                "id": profile["id"],
                "name": profile["name"],
                "version": profile["version"],
                "subjects": profile.get("subjects", []),
                "assessment": profile.get("assessment", {}),
                "sources": profile.get("sources", []),
            })
        except Exception:
            continue

    return {
        "success": True,
        "count": len(exams),
        "exams": exams,
        "engine": "PaperScope Versioned Exam Registry",
    }


@router.get("/{exam_id}")
def get_exam(exam_id: str):
    return {
        "success": True,
        "profile": _load_profile(exam_id),
    }


@router.post("/register")
def register_exam(request: ExamProfileRequest):
    try:
        profile = validate_exam_profile(request.profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    EXAM_DATA_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{profile['id']}__{profile['version']}.json"
    path = EXAM_DATA_DIR / filename

    path.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False)
    )

    return {
        "success": True,
        "message": "Exam profile registered.",
        "profile": profile,
    }


@router.post("/plan")
def create_plan(request: AssessmentPlanRequest):
    profile = _load_profile(request.exam)

    try:
        plan = build_assessment_plan(
            profile=profile,
            mode=request.mode,
            subject=request.subject,
            topic=request.topic,
            requested_count=request.requested_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "success": True,
        "plan": plan,
    }


@router.post("/learner-profile")
def learner_profile(request: LearnerExamRequest):
    profile = _load_profile(request.exam)

    try:
        result = build_learner_exam_profile(
            profile,
            request.exam_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "success": True,
        "learner_profile": result,
    }


@router.post("/compare")
def compare(request: CompareVersionsRequest):
    try:
        result = compare_syllabus_versions(
            request.old_profile,
            request.new_profile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "success": True,
        "comparison": result,
    }
