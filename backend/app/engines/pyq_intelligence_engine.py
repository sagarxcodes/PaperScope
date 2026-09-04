import re
from collections import Counter, defaultdict

from app.engines.material_engine import material_engine


YEAR_RE = re.compile(r"\b(20\d{2})\b")

QUESTION_RE = re.compile(
    r"^\\s*(?:Q(?:uestion)?\\s*)?(\\d{1,3})\\s*[\\).:\\-]\\s*(.+?)\\s*$",
    re.I | re.M,
)



def _normalize(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text


def _question_key(text):
    text = _normalize(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Remove common question-number-independent wording.
    text = re.sub(
        r"^(which of the following|what is|define|explain|describe)\s+",
        "",
        text,
    )

    return text


def _similarity(a, b):
    a_tokens = set(_question_key(a).split())
    b_tokens = set(_question_key(b).split())

    if not a_tokens or not b_tokens:
        return 0.0

    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def _extract_year(text="", filename=None):
    """
    Detect a four-digit year from the filename first,
    then from the document text.
    """

    for source in [str(filename or ""), str(text or "")[:2000]]:
        parts = re.split(r"[^0-9]+", source)

        for part in parts:
            if len(part) == 4 and part.startswith("20"):
                year = int(part)

                if 2000 <= year <= 2099:
                    return year

    return None


def _extract_questions(text):
    text = text or ""
    questions = []

    # Match numbered questions line-by-line.
    # Handles:
    # 1. Question
    # 2) Question
    # 3: Question
    # Q4. Question
    pattern = re.compile(
        r"(?m)^\s*(?:Q(?:uestion)?\s*)?(\d{1,3})\s*[\.\):\-]\s*(.+?)\s*$",
        re.I,
    )

    for match in pattern.finditer(text):
        number = int(match.group(1))
        question = _normalize(match.group(2))

        if len(question.split()) >= 3:
            questions.append({
                "number": number,
                "question": question,
            })

    # Fallback for questions appearing on the same line.
    if not questions:
        pattern = re.compile(
            r"(?:^|\s)(?:Q(?:uestion)?\s*)?(\d{1,3})\s*[\.\):\-]\s*"
            r"(.+?)(?=\s+(?:Q(?:uestion)?\s*)?\d{1,3}\s*[\.\):\-]|\Z)",
            re.I,
        )

        for match in pattern.finditer(text):
            number = int(match.group(1))
            question = _normalize(match.group(2))

            if len(question.split()) >= 3:
                questions.append({
                    "number": number,
                    "question": question,
                })

    return questions


def _concepts_for_question(question):
    try:
        analysis = material_engine.analyze(question)
        raw_concepts = analysis.get("key_concepts", [])
        raw_topics = analysis.get("topics", [])
    except Exception:
        raw_concepts = []
        raw_topics = []

    result = []

    # Extract clean concept names.
    for item in raw_concepts:
        if isinstance(item, dict):
            value = (
                item.get("concept")
                or item.get("name")
                or item.get("topic")
            )
        else:
            value = item

        if value:
            value = str(value).strip().lower()

            # Ignore question-command words.
            if value in {
                "explain",
                "define",
                "describe",
                "what",
                "why",
                "how",
                "discuss",
                "state",
                "identify",
                "calculate",
                "find",
            }:
                continue

            if len(value.split()) >= 1:
                result.append(value)

    # Topics returned by Material Intelligence are dictionaries.
    for item in raw_topics:
        if isinstance(item, dict):
            value = item.get("topic")
        else:
            value = item

        if value:
            value = str(value).strip()

            if value:
                result.append(value)

    # Preserve order while removing duplicates.
    cleaned = []

    for value in result:
        if value not in cleaned:
            cleaned.append(value)

    return cleaned[:5]


def _cluster_repeated_questions(all_questions):
    clusters = []

    for item in all_questions:
        best = None
        best_score = 0.0

        for cluster in clusters:
            score = _similarity(
                item["question"],
                cluster[0]["question"],
            )

            if score > best_score:
                best_score = score
                best = cluster

        if best is not None and best_score >= 0.55:
            best.append(item)
        else:
            clusters.append([item])

    return clusters


def analyze_pyq_documents(documents):
    """
    Analyze multiple PYQ documents.

    documents:
        [
            {
                "filename": "Probability_2024.txt",
                "text": "...",
                "year": 2024
            }
        ]
    """

    documents = documents or []

    extracted = []
    year_question_counts = Counter()
    concept_years = defaultdict(Counter)

    for document in documents:
        text = document.get("text", "")
        filename = document.get("filename", "")
        year = document.get("year") or _extract_year(text, filename)

        if not text:
            continue

        questions = _extract_questions(text)

        # If a document contains no obvious numbering, treat
        # meaningful sentences as question-like units.
        if not questions:
            sentences = material_engine.extract_sentences(text)

            for index, sentence in enumerate(sentences[:50], 1):
                if "?" in sentence:
                    questions.append({
                        "number": index,
                        "question": _normalize(sentence),
                    })

        for question in questions:
            concepts = _concepts_for_question(question["question"])

            item = {
                "year": year,
                "filename": filename,
                "number": question["number"],
                "question": question["question"],
                "concepts": concepts,
            }

            extracted.append(item)

            if year:
                year_question_counts[year] += 1

                for concept in concepts:
                    concept_years[concept][year] += 1

    clusters = _cluster_repeated_questions(extracted)

    repeated = []

    for cluster in clusters:
        if len(cluster) < 2:
            continue

        years = sorted({
            item["year"]
            for item in cluster
            if item.get("year")
        })

        repeated.append({
            "representative_question": cluster[0]["question"],
            "occurrences": len(cluster),
            "years": years,
            "questions": cluster,
        })

    concept_stats = []

    all_years = sorted(
        {
            item["year"]
            for item in extracted
            if item.get("year")
        }
    )

    for concept, yearly in concept_years.items():
        total = sum(yearly.values())
        appearances = len(yearly)

        if all_years:
            first = yearly.get(all_years[0], 0)
            last = yearly.get(all_years[-1], 0)
            trend = "increasing" if last > first else (
                "decreasing" if last < first else "stable"
            )
        else:
            trend = "unknown"

        # Simple transparent importance score.
        frequency_score = min(50, total * 10)
        appearance_score = min(30, appearances * 10)
        trend_score = (
            20 if trend == "increasing"
            else 10 if trend == "stable"
            else 5
        )

        importance = min(
            100,
            frequency_score + appearance_score + trend_score,
        )

        concept_stats.append({
            "concept": concept,
            "total_questions": total,
            "years_appeared": appearances,
            "year_distribution": dict(sorted(yearly.items())),
            "trend": trend,
            "importance_score": importance,
        })

    concept_stats.sort(
        key=lambda x: (
            -x["importance_score"],
            -x["total_questions"],
            x["concept"].lower(),
        )
    )

    predicted_topics = []

    for item in concept_stats[:10]:
        confidence = (
            "high" if item["importance_score"] >= 70
            else "medium" if item["importance_score"] >= 40
            else "low"
        )

        predicted_topics.append({
            "concept": item["concept"],
            "prediction_score": item["importance_score"],
            "confidence": confidence,
            "reason": (
                f"Appeared in {item['years_appeared']} year(s), "
                f"{item['total_questions']} time(s), "
                f"with a {item['trend']} trend."
            ),
        })

    return {
        "success": True,
        "engine": "PaperScope PYQ Intelligence Engine V1",
        "documents_analyzed": len(documents),
        "total_questions": len(extracted),
        "years": all_years,
        "year_wise_question_count": dict(
            sorted(year_question_counts.items())
        ),
        "questions": extracted,
        "repeated_questions": repeated,
        "concept_analysis": concept_stats,
        "predicted_topics": predicted_topics,
    }
