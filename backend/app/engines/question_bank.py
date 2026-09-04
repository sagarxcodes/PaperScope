import json
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[1]
QUESTION_BANK_PATH = BASE_DIR / "data" / "question_bank" / "questions.json"


def _load() -> List[Dict[str, Any]]:
    if not QUESTION_BANK_PATH.exists():
        return []

    try:
        data = json.loads(QUESTION_BANK_PATH.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(questions: List[Dict[str, Any]]) -> None:
    QUESTION_BANK_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUESTION_BANK_PATH.write_text(
        json.dumps(questions, indent=2, ensure_ascii=False)
    )


def add_question(question: Dict[str, Any]) -> Dict[str, Any]:
    questions = _load()

    question = dict(question)

    if "id" not in question:
        question["id"] = f"QB{len(questions) + 1:05d}"

    questions.append(question)
    _save(questions)

    return question


def add_questions(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    questions = _load()

    next_id = len(questions) + 1
    added = []

    for item in items:
        question = dict(item)

        if "id" not in question:
            question["id"] = f"QB{next_id:05d}"

        questions.append(question)
        added.append(question)
        next_id += 1

    _save(questions)

    return added


def get_all_questions() -> List[Dict[str, Any]]:
    return _load()


def get_question(question_id: str) -> Optional[Dict[str, Any]]:
    for question in _load():
        if str(question.get("id")) == str(question_id):
            return question

    return None


def search_questions(
    *,
    subject: Optional[str] = None,
    concept: Optional[str] = None,
    competency: Optional[str] = None,
    difficulty: Optional[str] = None,
    exam: Optional[str] = None,
    question_type: Optional[str] = None,
) -> List[Dict[str, Any]]:

    questions = _load()
    results = []

    for question in questions:

        if subject and str(question.get("subject", "")).lower() != subject.lower():
            continue

        if concept and concept.lower() not in str(
            question.get("concept", "")
        ).lower():
            continue

        if competency and competency.lower() not in str(
            question.get("competency", "")
        ).lower():
            continue

        if difficulty and str(
            question.get("difficulty", "")
        ).lower() != difficulty.lower():
            continue

        if exam and str(question.get("exam", "")).lower() != exam.lower():
            continue

        if question_type and str(
            question.get("question_type", "")
        ).lower() != question_type.lower():
            continue

        results.append(question)

    return results


def count_questions() -> int:
    return len(_load())


def get_statistics() -> Dict[str, Any]:
    questions = _load()

    stats = {
        "total": len(questions),
        "exams": {},
        "subjects": {},
        "concepts": {},
        "competencies": {},
        "difficulty": {},
        "question_types": {},
    }

    def count(bucket: Dict[str, int], value: Any):
        if value is None:
            return

        value = str(value).strip()

        if not value:
            return

        bucket[value] = bucket.get(value, 0) + 1

    for q in questions:
        count(stats["exams"], q.get("exam"))
        count(stats["subjects"], q.get("subject"))
        count(stats["concepts"], q.get("concept"))
        count(stats["competencies"], q.get("competency"))
        count(stats["difficulty"], q.get("difficulty"))
        count(stats["question_types"], q.get("question_type"))

    return stats
