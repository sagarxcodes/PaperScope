from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.engines.calendar_engine import (
    create_task,
    build_ai_tasks,
    summarize_tasks,
)


router = APIRouter(
    prefix="/api/calendar",
    tags=["Smart Calendar"],
)


class CalendarTaskRequest(BaseModel):
    title: str
    date: str
    start_time: Optional[str] = None
    duration_minutes: int = 60
    priority: str = "medium"
    category: str = "study"
    description: str = ""


class AICalendarRequest(BaseModel):
    competency_gaps: dict = {}
    pyq_analysis: dict = {}
    exam_date: Optional[str] = None
    where_you_stand: dict = {}


@router.post("/task")
def add_task(request: CalendarTaskRequest):
    try:
        task = create_task(
            title=request.title,
            date=request.date,
            start_time=request.start_time,
            duration_minutes=request.duration_minutes,
            priority=request.priority,
            category=request.category,
            source="manual",
            description=request.description,
        )

        return {
            "success": True,
            "task": task,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post("/generate")
def generate_ai_calendar(request: AICalendarRequest):
    tasks = build_ai_tasks(
        competency_gaps=request.competency_gaps,
        pyq_analysis=request.pyq_analysis,
        exam_date=request.exam_date,
        where_you_stand=request.where_you_stand,
    )

    return {
        "success": True,
        "engine": "PaperScope Smart Calendar Intelligence",
        "tasks": tasks,
        "summary": summarize_tasks(tasks),
    }


@router.post("/summary")
def calendar_summary(payload: dict):
    tasks = payload.get("tasks", [])

    return {
        "success": True,
        "summary": summarize_tasks(tasks),
    }
