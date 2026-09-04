from datetime import datetime, timedelta
from typing import Optional


PRIORITIES = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "must_study": 4,
}


def _normalise_priority(priority: str) -> str:
    value = (priority or "medium").strip().lower()

    aliases = {
        "must study": "must_study",
        "must-study": "must_study",
        "must": "must_study",
        "urgent": "must_study",
    }

    value = aliases.get(value, value)

    return value if value in PRIORITIES else "medium"


def create_task(
    title: str,
    date: str,
    start_time: Optional[str] = None,
    duration_minutes: int = 60,
    priority: str = "medium",
    category: str = "study",
    source: str = "manual",
    description: str = "",
):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must use YYYY-MM-DD format.")

    if start_time:
        try:
            datetime.strptime(start_time, "%H:%M")
        except ValueError:
            raise ValueError("Start time must use HH:MM format.")

    duration_minutes = max(15, min(int(duration_minutes), 480))

    return {
        "id": f"task_{int(datetime.now().timestamp() * 1000000000)}",
        "title": title.strip(),
        "date": date,
        "start_time": start_time,
        "duration_minutes": duration_minutes,
        "priority": _normalise_priority(priority),
        "category": category.strip() or "study",
        "source": source,
        "description": description.strip(),
        "completed": False,
    }


def _add_where_you_stand_tasks(
    tasks,
    where_you_stand,
    today,
):
    """
    Convert the learner's Where You Stand analysis into
    concrete, topic-specific calendar tasks.
    """

    if not isinstance(where_you_stand, dict):
        return

    topic_analysis = where_you_stand.get(
        "topic_analysis",
        {}
    )

    priority_topics = topic_analysis.get(
        "priority_topics",
        []
    )

    target_analysis = where_you_stand.get(
        "target_analysis",
        {}
    )

    current_standing = where_you_stand.get(
        "current_standing",
        {}
    )

    current_percentage = current_standing.get(
        "percentage",
        0
    )

    target_percentage = target_analysis.get(
        "target_percentage",
        80
    )

    improvement_needed = target_analysis.get(
        "improvement_percentage_points",
        max(0, target_percentage - current_percentage)
    )

    # Highest-gap topics first.
    for index, topic in enumerate(priority_topics[:5]):

        topic_name = topic.get(
            "topic",
            "Priority Topic"
        )

        accuracy = topic.get(
            "accuracy",
            0
        )

        gap = topic.get(
            "gap",
            max(0, 80 - accuracy)
        )

        priority = topic.get(
            "priority",
            "medium"
        )

        if gap <= 0:
            continue

        task_date = today + timedelta(
            days=index
        )

        if priority == "must_study":
            duration = 75
        elif priority == "high":
            duration = 60
        else:
            duration = 45

        tasks.append(
            create_task(
                title=f"Improve {topic_name}",
                date=task_date.isoformat(),
                start_time="09:00",
                duration_minutes=duration,
                priority=priority,
                category="where_you_stand",
                source="ai_where_you_stand",
                description=(
                    f"Targeted improvement for {topic_name}. "
                    f"Current topic accuracy: {accuracy}%. "
                    f"Estimated topic gap: {gap} percentage points. "
                    f"Overall standing: {current_percentage}%. "
                    f"Target: {target_percentage}%. "
                    f"Overall improvement needed: "
                    f"{improvement_needed} percentage points."
                ),
            )
        )


def build_ai_tasks(
    competency_gaps=None,
    pyq_analysis=None,
    exam_date=None,
    where_you_stand=None,
):
    """
    Convert PaperScope intelligence into actionable study tasks.

    Intelligence sources:
    - Where You Stand
    - Competency gaps
    - PYQ revision intelligence
    - Exam countdown
    """

    competency_gaps = competency_gaps or {}
    pyq_analysis = pyq_analysis or {}

    tasks = []

    today = datetime.now().date()

    # ---------------------------------------------------------
    # FALLBACK
    # ---------------------------------------------------------
    # The calendar must remain useful even when the frontend
    # sends an empty intelligence object. This prevents a blank
    # calendar caused by a missing Where You Stand payload.
    has_intelligence = bool(
        competency_gaps
        or pyq_analysis
        or exam_date
        or where_you_stand
    )

    if not has_intelligence:
        tasks.extend([
            create_task(
                title="Review weakest competency",
                date=today.isoformat(),
                start_time="09:00",
                duration_minutes=60,
                priority="high",
                category="adaptive_learning",
                source="ai_fallback",
                description=(
                    "Review the competency with the lowest current mastery "
                    "before starting the next targeted quiz."
                ),
            ),
            create_task(
                title="Complete targeted practice",
                date=(today + timedelta(days=1)).isoformat(),
                start_time="11:00",
                duration_minutes=60,
                priority="high",
                category="adaptive_learning",
                source="ai_fallback",
                description=(
                    "Complete a targeted practice session based on the "
                    "learner's current competency gap."
                ),
            ),
            create_task(
                title="Take adaptive quiz",
                date=(today + timedelta(days=2)).isoformat(),
                start_time="18:00",
                duration_minutes=45,
                priority="medium",
                category="assessment",
                source="ai_fallback",
                description=(
                    "Take the next PaperScope adaptive quiz and update "
                    "competency mastery."
                ),
            ),
        ])

        return tasks

    # ---------------------------------------------------------
    # WHERE YOU STAND
    # ---------------------------------------------------------

    _add_where_you_stand_tasks(
        tasks=tasks,
        where_you_stand=where_you_stand,
        today=today,
    )

    # ---------------------------------------------------------
    # COMPETENCY-DRIVEN TASKS
    # ---------------------------------------------------------

    if isinstance(competency_gaps, dict):
        gap_items = []

        for name, data in competency_gaps.items():

            if isinstance(data, dict):
                gap_score = data.get(
                    "gap_score",
                    data.get("severity", 0)
                )
            else:
                gap_score = data

            try:
                gap_score = float(gap_score)
            except (TypeError, ValueError):
                gap_score = 0

            gap_items.append(
                (name, gap_score)
            )

        gap_items.sort(
            key=lambda x: x[1],
            reverse=True
        )

        for index, (name, score) in enumerate(
            gap_items[:5]
        ):

            if score <= 0:
                continue

            task_date = today + timedelta(
                days=index
            )

            priority = (
                "must_study"
                if score >= 70
                else "high"
            )

            tasks.append(
                create_task(
                    title=f"Strengthen {name}",
                    date=task_date.isoformat(),
                    start_time="11:00",
                    duration_minutes=60,
                    priority=priority,
                    category="competency",
                    source="ai_competency",
                    description=(
                        "Targeted practice generated from "
                        "a PaperScope competency gap."
                    ),
                )
            )

    # ---------------------------------------------------------
    # PYQ-DRIVEN REVISION
    # ---------------------------------------------------------

    notes = pyq_analysis.get(
        "revision_notes",
        {}
    )

    notes = (
        notes.get("notes", [])
        if isinstance(notes, dict)
        else []
    )

    for index, note in enumerate(notes[:5]):

        concept = note.get(
            "concept",
            "Priority topic"
        )

        priority_map = {
            "Must Study": "must_study",
            "High Priority": "high",
            "Review": "medium",
        }

        priority = priority_map.get(
            note.get("priority"),
            "medium"
        )

        task_date = today + timedelta(
            days=index
        )

        tasks.append(
            create_task(
                title=f"Revise {concept}",
                date=task_date.isoformat(),
                start_time="14:00",
                duration_minutes=45,
                priority=priority,
                category="pyq_revision",
                source="ai_pyq",
                description=note.get(
                    "revision_note",
                    "Review this topic using "
                    "historical question evidence."
                ),
            )
        )

    # ---------------------------------------------------------
    # EXAM COUNTDOWN
    # ---------------------------------------------------------

    if exam_date:

        try:
            target = datetime.strptime(
                exam_date,
                "%Y-%m-%d"
            ).date()

            days_remaining = (
                target - today
            ).days

            if days_remaining >= 0:

                tasks.append(
                    create_task(
                        title="Exam Preparation Checkpoint",
                        date=exam_date,
                        start_time="19:00",
                        duration_minutes=30,
                        priority="must_study",
                        category="exam",
                        source="ai_exam",
                        description=(
                            "Final preparation checkpoint. "
                            f"{days_remaining} day(s) remaining."
                        ),
                    )
                )

        except ValueError:
            pass

    return tasks


def summarize_tasks(tasks):

    total = len(tasks)

    completed = sum(
        1
        for task in tasks
        if task.get("completed")
    )

    by_priority = {}

    for task in tasks:

        priority = task.get(
            "priority",
            "medium"
        )

        by_priority[priority] = (
            by_priority.get(priority, 0) + 1
        )

    by_category = {}

    for task in tasks:

        category = task.get(
            "category",
            "study"
        )

        by_category[category] = (
            by_category.get(category, 0) + 1
        )

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": total - completed,
        "completion_percentage": (
            round(
                (completed / total) * 100
            )
            if total
            else 0
        ),
        "by_priority": by_priority,
        "by_category": by_category,
    }
