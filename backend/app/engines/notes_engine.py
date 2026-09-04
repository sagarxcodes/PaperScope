"""
PaperScope — AI Notes Intelligence

Creates structured, revision-oriented notes from learning material.

The engine is exam-agnostic. Exam context and syllabus taxonomy are
provided as data rather than hard-coded.
"""

import re
from typing import Any, Dict, List, Optional


STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from",
    "are", "was", "were", "have", "has", "had", "into",
    "their", "there", "which", "when", "where", "what",
    "about", "than", "then", "they", "them", "these",
    "those", "such", "also", "can", "may", "will", "would",
    "should", "could", "been", "being", "its", "our", "your",
    "you", "not", "but", "all", "any", "one", "two", "three",
}


def _clean(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _sentences(text: str) -> List[str]:
    text = _clean(text)

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    return [
        part.strip()
        for part in parts
        if len(part.strip()) >= 20
    ]


def _words(text: str) -> List[str]:
    return re.findall(
        r"\b[A-Za-z][A-Za-z'-]{2,}\b",
        text.lower(),
    )


def _keywords(text: str, limit: int = 12) -> List[str]:
    words = _words(text)

    frequency: Dict[str, int] = {}

    for word in words:
        if word in STOPWORDS:
            continue

        frequency[word] = frequency.get(word, 0) + 1

    ranked = sorted(
        frequency.items(),
        key=lambda item: (-item[1], item[0]),
    )

    return [
        word
        for word, _ in ranked[:limit]
    ]


def _extract_definitions(
    sentences: List[str],
) -> List[str]:

    patterns = [
        r"\bis defined as\b",
        r"\brefers to\b",
        r"\bmeans\b",
        r"\bis known as\b",
        r"\bcan be defined as\b",
    ]

    result = []

    for sentence in sentences:
        lower = sentence.lower()

        if any(
            re.search(pattern, lower)
            for pattern in patterns
        ):
            result.append(sentence)

    return result[:8]


def _extract_formulas(text: str) -> List[str]:

    lines = str(text or "").splitlines()
    formulas = []

    for line in lines:
        clean = line.strip()

        if not clean:
            continue

        # Detect common mathematical/formula signals.
        if (
            "=" in clean
            or "∝" in clean
            or "→" in clean
            or "≤" in clean
            or "≥" in clean
            or re.search(r"\bP\([^)]+\)", clean)
        ):
            if 3 <= len(clean) <= 250:
                formulas.append(clean)

    return list(dict.fromkeys(formulas))[:15]


def _extract_processes(
    sentences: List[str],
) -> List[str]:

    signals = [
        "first",
        "second",
        "third",
        "step",
        "then",
        "finally",
        "process",
        "procedure",
        "method",
        "followed by",
    ]

    result = []

    for sentence in sentences:
        lower = sentence.lower()

        if any(signal in lower for signal in signals):
            result.append(sentence)

    return result[:10]


def _extract_examples(
    sentences: List[str],
) -> List[str]:

    result = []

    for sentence in sentences:
        lower = sentence.lower()

        if (
            "for example" in lower
            or "for instance" in lower
            or "example:" in lower
            or lower.startswith("eg ")
        ):
            result.append(sentence)

    return result[:8]


def _extract_important_facts(
    sentences: List[str],
) -> List[str]:

    signals = [
        "important",
        "key",
        "note that",
        "remember",
        "significant",
        "must",
        "always",
        "never",
        "principle",
        "law",
    ]

    result = []

    for sentence in sentences:
        lower = sentence.lower()

        if any(
            signal in lower
            for signal in signals
        ):
            result.append(sentence)

    return result[:10]


def _build_summary(
    sentences: List[str],
) -> str:

    if not sentences:
        return "No meaningful learning content was detected."

    # Deterministic extractive summary for the local MVP.
    selected = sentences[:4]

    return " ".join(selected)


def _match_syllabus(
    keywords: List[str],
    syllabus: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    if not isinstance(syllabus, dict):
        return []

    matches = []

    keyword_set = set(keywords)

    for subject, topics in syllabus.items():

        if isinstance(topics, list):

            for topic in topics:
                topic_words = set(
                    _words(str(topic))
                )

                overlap = keyword_set & topic_words

                if overlap:
                    matches.append({
                        "subject": str(subject),
                        "topic": str(topic),
                        "match_score": len(overlap),
                    })

        elif isinstance(topics, dict):

            for topic, subtopics in topics.items():

                topic_words = set(
                    _words(str(topic))
                )

                overlap = keyword_set & topic_words

                if overlap:
                    matches.append({
                        "subject": str(subject),
                        "topic": str(topic),
                        "subtopics": (
                            subtopics
                            if isinstance(subtopics, list)
                            else []
                        ),
                        "match_score": len(overlap),
                    })

    matches.sort(
        key=lambda x: x["match_score"],
        reverse=True,
    )

    return matches[:10]


def build_ai_notes(
    text: str,
    exam_profile: Optional[Dict[str, Any]] = None,
    material_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    text = _clean(text)
    sentences = _sentences(text)
    keywords = _keywords(text)

    syllabus = {}

    if exam_profile:
        syllabus = exam_profile.get(
            "syllabus",
            {},
        )

    syllabus_matches = _match_syllabus(
        keywords,
        syllabus,
    )

    definitions = _extract_definitions(
        sentences
    )

    formulas = _extract_formulas(
        text
    )

    processes = _extract_processes(
        sentences
    )

    examples = _extract_examples(
        sentences
    )

    important_facts = _extract_important_facts(
        sentences
    )

    # Revision checklist is deliberately actionable.
    revision_checklist = []

    if definitions:
        revision_checklist.append(
            "Review the core definitions."
        )

    if formulas:
        revision_checklist.append(
            "Memorize and practice the important formulas."
        )

    if processes:
        revision_checklist.append(
            "Reproduce the important processes without notes."
        )

    if examples:
        revision_checklist.append(
            "Solve or explain the examples independently."
        )

    if not revision_checklist:
        revision_checklist.append(
            "Re-read the key concepts and test yourself."
        )

    competencies = []

    for match in syllabus_matches[:5]:
        competency = match["topic"]

        competencies.append({
            "competency": competency,
            "subject": match["subject"],
            "match_score": match["match_score"],
            "source": "syllabus_match",
        })

    return {
        "status": "ready",
        "engine": "PaperScope AI Notes Intelligence",
        "exam": (
            exam_profile.get("name")
            if exam_profile
            else None
        ),
        "material": {
            "characters": len(text),
            "words": len(_words(text)),
            "sentences": len(sentences),
        },
        "summary": _build_summary(sentences),
        "key_concepts": keywords,
        "definitions": definitions,
        "formulas": formulas,
        "important_facts": important_facts,
        "processes": processes,
        "examples": examples,
        "syllabus_matches": syllabus_matches,
        "competencies": competencies,
        "revision_checklist": revision_checklist,
        "material_analysis": material_analysis or {},
    }
