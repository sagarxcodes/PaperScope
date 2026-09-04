from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.engines.notes_engine import build_ai_notes

router = APIRouter(
    prefix="/api/notes",
    tags=["AI Notes"],
)


class NotesRequest(BaseModel):
    text: str
    exam_profile: Optional[Dict[str, Any]] = None
    material_analysis: Optional[Dict[str, Any]] = None


@router.post("/generate")
def generate_notes(request: NotesRequest):
    notes = build_ai_notes(
        text=request.text,
        exam_profile=request.exam_profile,
        material_analysis=request.material_analysis,
    )

    return {
        "success": True,
        "notes": notes,
    }
