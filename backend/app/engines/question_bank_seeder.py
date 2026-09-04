import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from app.engines.question_bank import add_questions


REQUIRED_FIELDS = {
    "question",
    "options",
    "answer",
}


def _normalise_question(item: Dict[str, Any]) -> Dict[str, Any]:
    q = dict(item)

    # Ensure options are stored as a list.
    if isinstance(q.get("options"), str):
        try:
            q["options"] = json.loads(q["options"])
        except Exception:
            q["options"] = [
                x.strip()
                for x in q["options"].split("|")
                if x.strip()
            ]

    # Ensure answer is an integer index.
    if isinstance(q.get("answer"), str):
        value = q["answer"].strip()

        if value.upper() in {"A", "B", "C", "D"}:
            q["answer"] = ord(value.upper()) - ord("A")
        else:
            try:
                q["answer"] = int(value)
            except ValueError:
                pass

    q.setdefault("exam", "Unknown")
    q.setdefault("year", None)
    q.setdefault("subject", "Unknown")
    q.setdefault("concept", "Unclassified")
    q.setdefault("sub_concept", "")
    q.setdefault("competency", "Unclassified competency")
    q.setdefault("difficulty", "medium")
    q.setdefault("question_type", "mcq")
    q.setdefault("explanation", "")
    q.setdefault("source", "Unknown")

    return q


def validate_question(q: Dict[str, Any]) -> bool:

    if not all(field in q for field in REQUIRED_FIELDS):
        return False

    if not isinstance(q.get("options"), list):
        return False

    if len(q["options"]) != 4:
        return False

    answer = q.get("answer")

    if not isinstance(answer, int):
        return False

    if answer < 0 or answer >= len(q["options"]):
        return False

    if len(set(str(x).strip().lower() for x in q["options"])) != 4:
        return False

    return True


def seed_json(path: str) -> Dict[str, Any]:

    file_path = Path(path)

    data = json.loads(file_path.read_text())

    if not isinstance(data, list):
        raise ValueError("JSON question bank must contain a list.")

    valid = []
    rejected = []

    for item in data:

        q = _normalise_question(item)

        if validate_question(q):
            valid.append(q)
        else:
            rejected.append(q)

    added = add_questions(valid)

    return {
        "source": str(file_path),
        "loaded": len(data),
        "valid": len(valid),
        "rejected": len(rejected),
        "added": len(added),
    }


def seed_csv(path: str) -> Dict[str, Any]:

    file_path = Path(path)

    rows = []

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            rows.append(_normalise_question(row))

    valid = [
        q for q in rows
        if validate_question(q)
    ]

    rejected = len(rows) - len(valid)

    added = add_questions(valid)

    return {
        "source": str(file_path),
        "loaded": len(rows),
        "valid": len(valid),
        "rejected": rejected,
        "added": len(added),
    }
