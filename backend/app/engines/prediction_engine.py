import re
from collections import Counter


def _normalize(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text


def _difficulty_from_question(question):
    q = question.lower()

    hard_signals = [
        "calculate",
        "derive",
        "prove",
        "compare",
        "analyze",
        "evaluate",
        "interpret",
        "regression",
        "hypothesis",
        "variance",
        "estimation",
    ]

    medium_signals = [
        "explain",
        "describe",
        "discuss",
        "differentiate",
        "relationship",
        "application",
    ]

    if any(word in q for word in hard_signals):
        return "Hard"

    if any(word in q for word in medium_signals):
        return "Medium"

    return "Easy"


def _question_type(question):
    q = question.lower().strip()

    if q.startswith("define") or q.startswith("what is"):
        return "Definition"

    if q.startswith("explain") or q.startswith("describe"):
        return "Conceptual"

    if q.startswith("calculate") or q.startswith("find"):
        return "Numerical"

    if q.startswith("compare") or q.startswith("differentiate"):
        return "Comparison"

    if q.startswith("analyze") or q.startswith("evaluate"):
        return "Analytical"

    return "Conceptual"


def _score_question(
    question,
    concept,
    concept_score,
    repeated_count,
    years_count,
    total_years,
    trend="unknown",
):
    """
    Evidence-weighted prediction score.

    Specific question evidence has priority over broad concept evidence.
    """

    total_years = max(1, total_years)

    # Specific historical recurrence.
    recurrence_score = min(45, repeated_count * 15)

    # Cross-year consistency.
    year_score = min(25, years_count * 8)

    # Concept importance contributes, but cannot dominate.
    concept_score_component = min(20, concept_score * 0.20)

    # Trend provides a smaller signal.
    trend_score = (
        10 if trend == "increasing"
        else 6 if trend == "stable"
        else 2 if trend == "decreasing"
        else 0
    )

    score = (
        recurrence_score
        + year_score
        + concept_score_component
        + trend_score
    )

    return min(100, round(score))


def generate_predicted_paper(pyq_analysis, max_questions=10):
    """
    Generate a predicted paper from previously analysed PYQs.

    The prediction is derived only from uploaded-question evidence.
    No fixed question list is used.
    """

    questions = pyq_analysis.get("questions", []) or []
    concept_analysis = pyq_analysis.get("concept_analysis", []) or []
    repeated_questions = pyq_analysis.get("repeated_questions", []) or []
    years = pyq_analysis.get("years", []) or []

    if not questions:
        return {
            "success": False,
            "message": "No questions were available for prediction.",
            "predicted_questions": [],
        }

    concept_scores = {
        str(item.get("concept", "")).strip().lower(): item
        for item in concept_analysis
        if item.get("concept")
    }

    repeated_by_question = {}

    for item in repeated_questions:
        representative = _normalize(
            item.get("representative_question")
            or item.get("question")
            or ""
        )

        if representative:
            repeated_by_question[representative.lower()] = item

    candidates = []

    for item in questions:
        question = _normalize(item.get("question", ""))

        if not question:
            continue

        concepts = item.get("concepts", []) or []

        best_concept = None
        best_concept_data = None

        for concept in concepts:
            key = str(concept).strip().lower()
            if key in concept_scores:
                data = concept_scores[key]

                if (
                    best_concept_data is None
                    or data.get("importance_score", 0)
                    > best_concept_data.get("importance_score", 0)
                ):
                    best_concept = concept
                    best_concept_data = data

        if best_concept_data is None and concepts:
            best_concept = concepts[0]

        concept_score = (
            best_concept_data.get("importance_score", 30)
            if best_concept_data
            else 30
        )

        repeated_count = 0
        repeated_years = []

        for representative, repeated in repeated_by_question.items():
            words_a = set(re.sub(r"[^a-z0-9 ]", " ", question.lower()).split())
            words_b = set(re.sub(r"[^a-z0-9 ]", " ", representative).split())

            if words_a and words_b:
                similarity = len(words_a & words_b) / len(words_a | words_b)

                if similarity >= 0.55:
                    repeated_count = repeated.get(
                        "occurrences",
                        repeated.get("count", 1),
                    )
                    repeated_years = repeated.get("years", []) or []
                    break

        years_count = len(repeated_years)

        concept_trend = (
            best_concept_data.get("trend", "unknown")
            if best_concept_data
            else "unknown"
        )

        prediction_score = _score_question(
            question,
            best_concept or "General",
            concept_score,
            repeated_count,
            years_count,
            len(years),
            concept_trend,
        )

        if prediction_score >= 80:
            confidence = "Very High"
        elif prediction_score >= 60:
            confidence = "High"
        elif prediction_score >= 40:
            confidence = "Medium"
        else:
            confidence = "Low"

        reason_parts = []

        if repeated_count >= 2:
            reason_parts.append(
                f"similar question appeared {repeated_count} times"
            )

        if years_count >= 2:
            reason_parts.append(
                f"appeared across {years_count} years"
            )

        if best_concept_data:
            reason_parts.append(
                f"concept importance score is {concept_score}"
            )

            trend = best_concept_data.get("trend")
            if trend and trend != "unknown":
                reason_parts.append(f"trend is {trend}")

        if not reason_parts:
            reason_parts.append(
                "supported by concept-level evidence from uploaded papers"
            )

        candidates.append({
            "predicted_question": question,
            "concept": best_concept or "General",
            "prediction_score": prediction_score,
            "confidence": confidence,
            "difficulty": _difficulty_from_question(question),
            "question_type": _question_type(question),
            "evidence_years": repeated_years or (
                [item.get("year")]
                if item.get("year")
                else []
            ),
            "evidence_occurrences": repeated_count or 1,
            "reason": "; ".join(reason_parts) + ".",
        })

    # Highest-evidence questions first.
    candidates.sort(
        key=lambda x: (
            -x["prediction_score"],
            -x["evidence_occurrences"],
            x["predicted_question"].lower(),
        )
    )

    # Remove near-duplicate predicted questions.
    selected = []

    for candidate in candidates:
        duplicate = False

        candidate_words = set(
            re.sub(
                r"[^a-z0-9 ]",
                " ",
                candidate["predicted_question"].lower(),
            ).split()
        )

        for existing in selected:
            existing_words = set(
                re.sub(
                    r"[^a-z0-9 ]",
                    " ",
                    existing["predicted_question"].lower(),
                ).split()
            )

            if candidate_words and existing_words:
                similarity = len(
                    candidate_words & existing_words
                ) / len(candidate_words | existing_words)

                if similarity >= 0.70:
                    duplicate = True
                    break

        if not duplicate:
            selected.append(candidate)

        if len(selected) >= max_questions:
            break

    # Ensure concept diversity where possible.
    diversified = []
    used_concepts = set()

    for item in selected:
        concept = item["concept"].lower()

        if concept not in used_concepts or len(diversified) < 3:
            diversified.append(item)
            used_concepts.add(concept)

    # If diversity filtering removed too much, restore remaining high-score items.
    for item in selected:
        if item not in diversified:
            diversified.append(item)

        if len(diversified) >= max_questions:
            break

    difficulty_distribution = Counter(
        item["difficulty"] for item in diversified
    )

    confidence_distribution = Counter(
        item["confidence"] for item in diversified
    )

    high_priority = [
        item for item in diversified
        if item["confidence"] in {"Very High", "High"}
    ]

    return {
        "success": True,
        "engine": "PaperScope Evidence-Based Prediction Engine V2",
        "source_years": years,
        "questions_considered": len(questions),
        "predicted_questions": diversified,
        "high_priority_questions": high_priority,
        "total_predicted": len(diversified),
        "difficulty_distribution": dict(difficulty_distribution),
        "confidence_distribution": dict(confidence_distribution),
        "prediction_method": [
            "concept frequency",
            "cross-year recurrence",
            "trend analysis",
            "question repetition",
            "evidence-weighted scoring",
        ],
    }


def generate_revision_notes(pyq_analysis):
    """
    Generate evidence-based revision notes from PYQ intelligence.

    Notes are derived from:
    - concept frequency
    - number of years appearing
    - repeated questions
    - historical trend
    - importance score
    """

    concept_analysis = pyq_analysis.get("concept_analysis", []) or []
    repeated_questions = pyq_analysis.get("repeated_questions", []) or []
    years = pyq_analysis.get("years", []) or []

    repeated_by_concept = {}

    for item in repeated_questions:
        question = _normalize(
            item.get("representative_question")
            or item.get("question")
            or ""
        )

        if not question:
            continue

        occurrences = item.get(
            "occurrences",
            item.get("count", 1)
        )

        question_years = item.get("years", []) or []

        repeated_by_concept[question.lower()] = {
            "question": question,
            "occurrences": occurrences,
            "years": question_years,
        }

    notes = []

    for concept in concept_analysis[:10]:
        name = _normalize(concept.get("concept", ""))
        if not name:
            continue

        score = int(concept.get("importance_score", 0))
        trend = concept.get("trend", "unknown")
        years_appeared = int(concept.get("years_appeared", 0))
        frequency = int(concept.get("total_questions", 0))

        if score >= 70:
            priority = "Must Study"
        elif score >= 40:
            priority = "High Priority"
        else:
            priority = "Review"

        if trend == "increasing":
            trend_message = (
                f"The concept is gaining importance, appearing more recently "
                f"than in earlier papers."
            )
        elif trend == "decreasing":
            trend_message = (
                f"The concept has appeared less frequently in later papers, "
                f"but should still be reviewed."
            )
        elif trend == "stable":
            trend_message = (
                f"The concept has remained consistently represented across "
                f"the analysed papers."
            )
        else:
            trend_message = "There is insufficient trend evidence."

        matching_repeated = []

        concept_words = set(
            re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
        )

        for repeated in repeated_by_concept.values():
            question_words = set(
                re.sub(
                    r"[^a-z0-9 ]",
                    " ",
                    repeated["question"].lower()
                ).split()
            )

            if concept_words and question_words:
                overlap = len(
                    concept_words & question_words
                ) / len(concept_words | question_words)

                if overlap >= 0.20 or name.lower() in repeated["question"].lower():
                    matching_repeated.append(repeated)

        repeated_evidence = [
            {
                "question": item["question"],
                "occurrences": item["occurrences"],
                "years": item["years"],
            }
            for item in matching_repeated[:3]
        ]

        if frequency >= 3:
            study_focus = (
                f"Focus strongly on the definition, core principles, "
                f"applications and common exam question patterns for {name}."
            )
        elif frequency == 2:
            study_focus = (
                f"Understand the fundamentals of {name}, its applications, "
                f"and how it can be tested in conceptual or analytical questions."
            )
        else:
            study_focus = (
                f"Review the fundamentals, terminology and typical applications "
                f"of {name}."
            )

        if matching_repeated:
            evidence_message = (
                f"Related question patterns were repeated across "
                f"{len(matching_repeated)} detected cluster(s)."
            )
        else:
            evidence_message = (
                f"The concept is supported by {frequency} historical "
                f"question occurrence(s)."
            )

        notes.append({
            "concept": name,
            "priority": priority,
            "importance_score": score,
            "years_appeared": years_appeared,
            "question_frequency": frequency,
            "trend": trend,
            "study_focus": study_focus,
            "evidence": evidence_message,
            "trend_analysis": trend_message,
            "repeated_questions": repeated_evidence,
            "revision_note": (
                f"{study_focus} {trend_message} "
                f"{evidence_message}"
            ),
        })

    priority_order = {
        "Must Study": 0,
        "High Priority": 1,
        "Review": 2,
    }

    notes.sort(
        key=lambda x: (
            priority_order.get(x["priority"], 3),
            -x["importance_score"],
            -x["question_frequency"],
        )
    )

    return {
        "success": True,
        "engine": "PaperScope Evidence-Based Revision Notes Engine V2",
        "source_years": years,
        "concepts_analysed": len(concept_analysis),
        "notes": notes,
    }

