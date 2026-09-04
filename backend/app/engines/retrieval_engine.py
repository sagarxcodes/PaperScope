import re
from typing import Any, Dict, List, Optional

from app.engines.question_bank import get_all_questions


STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "be", "by", "with", "from", "as",
    "that", "this", "these", "those", "can", "also", "used", "use",
    "which", "what", "how", "about", "their", "into", "through",
}


def _tokens(text: str) -> set:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]*", str(text or "").lower())
    return {
        w for w in words
        if len(w) > 2 and w not in STOPWORDS
    }


def _similarity(a: str, b: str) -> float:
    ta = _tokens(a)
    tb = _tokens(b)

    if not ta or not tb:
        return 0.0

    intersection = len(ta & tb)
    union = len(ta | tb)

    return intersection / union if union else 0.0


def _question_text(q: Dict[str, Any]) -> str:
    return " ".join([
        str(q.get("question", "")),
        str(q.get("subject", "")),
        str(q.get("concept", "")),
        str(q.get("sub_concept", "")),
        str(q.get("competency", "")),
        str(q.get("question_type", "")),
    ])


def retrieve_questions(
    query: str,
    *,
    top_k: int = 5,
    concept: Optional[str] = None,
    competency: Optional[str] = None,
    difficulty: Optional[str] = None,
    subject: Optional[str] = None,
    exam: Optional[str] = None,
) -> List[Dict[str, Any]]:

    questions = get_all_questions()

    scored = []

    for q in questions:

        score = _similarity(query, _question_text(q))

        # Metadata boosts.
        if concept:
            if concept.lower() in str(q.get("concept", "")).lower():
                score += 0.35

        if competency:
            if competency.lower() in str(q.get("competency", "")).lower():
                score += 0.30

        if subject:
            if subject.lower() == str(q.get("subject", "")).lower():
                score += 0.20

        if difficulty:
            if difficulty.lower() == str(q.get("difficulty", "")).lower():
                score += 0.10

        if exam:
            if exam.lower() == str(q.get("exam", "")).lower():
                score += 0.05

        scored.append((score, q))

    scored.sort(key=lambda item: item[0], reverse=True)

    results = []

    for score, q in scored[:top_k]:
        item = dict(q)
        item["_retrieval_score"] = round(score, 4)
        results.append(item)

    return results


def retrieve_by_concept(
    concept: str,
    *,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    return retrieve_questions(
        concept,
        concept=concept,
        top_k=top_k,
    )


def retrieve_by_competency(
    competency: str,
    *,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    return retrieve_questions(
        competency,
        competency=competency,
        top_k=top_k,
    )


def retrieve_similar(
    question: Dict[str, Any],
    *,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    query = _question_text(question)

    return retrieve_questions(
        query,
        top_k=top_k,
        concept=question.get("concept"),
        competency=question.get("competency"),
        difficulty=question.get("difficulty"),
        subject=question.get("subject"),
    )
