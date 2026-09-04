from typing import Any, Dict, List

from app.engines.question_bank import get_all_questions
from app.engines.retrieval_engine import retrieve_questions
from app.engines.competency_ontology import match_question
from app.engines.adaptive_question_engine import build_adaptive_question_plan


def analyze_question_intelligence(
    text: str,
    concepts: List[Dict[str, Any]] = None,
    competencies: List[Dict[str, Any]] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Connects PaperScope's question-bank, retrieval,
    competency and adaptive-question engines.
    """

    concepts = concepts or []
    competencies = competencies or []

    all_questions = get_all_questions()

    retrieved: List[Dict[str, Any]] = []

    # 1. Retrieve questions using the uploaded material
    if text.strip():
        retrieved = retrieve_questions(
            text,
            top_k=top_k,
            subject="Official Statistics",
        )

    # 2. Retrieve additional questions from detected concepts
    for concept in concepts:
        concept_name = (
            concept.get("concept")
            or concept.get("name")
            or concept.get("term")
        )

        if not concept_name:
            continue

        matches = retrieve_questions(
            concept_name,
            top_k=top_k,
            concept=concept_name,
            subject="Official Statistics",
        )

        existing_ids = {
            q.get("id") for q in retrieved
        }

        for item in matches:
            if item.get("id") not in existing_ids:
                retrieved.append(item)

    # 3. Attach competency matches
    enriched_questions = []

    for item in retrieved:
        q = dict(item)

        try:
            competency_matches = match_question(q)
        except Exception:
            competency_matches = []

        # Keep the strongest competency match as primary.
        # Secondary matches are retained only when they are
        # clearly relevant to the question concept.
        primary = competency_matches[:1]
        secondary = []

        question_concept = str(q.get("concept", "")).lower().strip()

        for match in competency_matches[1:]:
            match_concept = str(match.get("concept", "")).lower().strip()
            if match_concept == question_concept:
                secondary.append(match)

        q["competency_matches"] = primary + secondary
        q["primary_competency"] = (
            primary[0].get("competency")
            if primary
            else None
        )
        enriched_questions.append(q)

    # 4. Build a lightweight competency-performance
    # structure when actual assessment results are not available.
    competency_result = {
        "competencies": competencies,
        "gaps": [],
        "strengths": [],
        "total_competencies": len(competencies),
        "gap_count": 0,
    }

    # 5. Prepare adaptive plan only when competency gaps
    # are available from a previous assessment.
    adaptive_plan = build_adaptive_question_plan(
        competency_result,
        all_questions,
        questions_per_gap=3,
    )

    return {
        "question_bank": {
            "total_questions": len(all_questions),
        },
        "retrieval": {
            "query": text[:500],
            "retrieved_count": len(enriched_questions),
            "questions": enriched_questions,
        },
        "adaptive": adaptive_plan,
    }
