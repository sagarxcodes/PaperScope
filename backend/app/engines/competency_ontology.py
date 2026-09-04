import json
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[1]
COMPETENCY_PATH = BASE_DIR / "data" / "competencies" / "competencies.json"


def _load() -> List[Dict[str, Any]]:
    if not COMPETENCY_PATH.exists():
        return []

    try:
        data = json.loads(COMPETENCY_PATH.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def get_all_competencies() -> List[Dict[str, Any]]:
    return _load()


def get_competency(comp_id: str) -> Optional[Dict[str, Any]]:
    for item in _load():
        if item.get("id") == comp_id:
            return item
    return None


def find_by_concept(
    concept: str,
    subject: Optional[str] = None,
) -> List[Dict[str, Any]]:

    concept = str(concept or "").lower()

    results = []

    for item in _load():

        if concept not in str(item.get("concept", "")).lower():
            continue

        if subject:
            if str(item.get("subject", "")).lower() != subject.lower():
                continue

        results.append(item)

    return results


def find_by_skill(skill: str) -> List[Dict[str, Any]]:

    skill = str(skill or "").lower()

    results = []

    for item in _load():

        skills = item.get("skills", [])

        if any(skill in str(s).lower() for s in skills):
            results.append(item)

    return results


def search_competencies(query: str) -> List[Dict[str, Any]]:

    query = str(query or "").lower()

    terms = set(query.split())

    scored = []

    for item in _load():

        searchable = " ".join([
            str(item.get("subject", "")),
            str(item.get("concept", "")),
            str(item.get("sub_concept", "")),
            str(item.get("competency", "")),
            str(item.get("description", "")),
            " ".join(item.get("skills", [])),
        ]).lower()

        score = sum(1 for term in terms if term in searchable)

        if score:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [item for _, item in scored]


def match_question(question: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Map a question's metadata to relevant competencies.
    """

    concept = str(question.get("concept", "")).lower()
    competency = str(question.get("competency", "")).lower()
    sub_concept = str(question.get("sub_concept", "")).lower()

    scored = []

    for item in _load():

        score = 0

        if concept and concept in str(item.get("concept", "")).lower():
            score += 5

        if sub_concept and sub_concept in str(
            item.get("sub_concept", "")
        ).lower():
            score += 4

        if competency and competency in str(
            item.get("competency", "")
        ).lower():
            score += 6

        if score:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [item for _, item in scored]


def get_statistics() -> Dict[str, Any]:

    items = _load()

    return {
        "total_competencies": len(items),
        "subjects": sorted({
            item.get("subject")
            for item in items
            if item.get("subject")
        }),
        "concepts": sorted({
            item.get("concept")
            for item in items
            if item.get("concept")
        }),
        "skills": sorted({
            skill
            for item in items
            for skill in item.get("skills", [])
        }),
    }
