import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parents[1]
PATTERN_PATH = BASE_DIR / "data" / "question_bank" / "knowledge_patterns.json"


def _load_patterns() -> List[Dict[str, Any]]:
    try:
        data = json.loads(PATTERN_PATH.read_text())
        return data.get("patterns", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _mastery(profile: Dict[str, Any], concept: str) -> float:
    target = _norm(concept)

    for key, value in (profile.get("mastery") or {}).items():
        if _norm(key) == target:
            try:
                return float(value)
            except Exception:
                pass

    return 50.0


def _difficulty(profile: Dict[str, Any], concept: str) -> str:
    m = _mastery(profile, concept)

    if m < 50:
        return "easy"
    if m < 70:
        return "medium"
    return "hard"


def _family(concept: str) -> str:
    c = _norm(concept)

    if any(x in c for x in [
        "conditional probability",
        "bayes",
        "probability",
        "random variable",
        "independence"
    ]):
        return "probability"

    if any(x in c for x in [
        "sampling",
        "sample",
        "population",
        "stratified",
        "cluster",
        "systematic sampling"
    ]):
        return "sampling"

    if any(x in c for x in [
        "quality",
        "timeliness",
        "accuracy",
        "relevance",
        "coherence",
        "accessibility"
    ]):
        return "data_quality"

    if any(x in c for x in [
        "official statistics",
        "administrative data",
        "census",
        "survey"
    ]):
        return "official_statistics"

    if any(x in c for x in [
        "production process",
        "statistical process",
        "data production",
        "dissemination",
        "collection",
        "processing"
    ]):
        return "statistical_process"

    if any(x in c for x in [
        "data analysis",
        "mean",
        "median",
        "variance",
        "correlation",
        "regression"
    ]):
        return "data_analysis"

    return "general"


def _mcq(
    question: str,
    correct: str,
    distractors: List[str],
    concept: str,
    difficulty: str,
    explanation: str,
    pattern: str,
) -> Dict[str, Any]:

    options = [correct] + distractors[:3]

    # Deterministic shuffle so answer index is not always zero.
    seed = hash(question) % (2**32)
    rng = random.Random(seed)
    rng.shuffle(options)

    answer_index = options.index(correct)

    return {
        "question": question,
        "options": options,
        "answer": answer_index,
        "correct_answer": correct,
        "distractors": [
            x for x in options if x != correct
        ],
        "explanation": explanation,
        "concept": concept,
        "competency": concept,
        "target_competency": concept,
        "difficulty": difficulty,
        "question_type": "application",
        "generation": {
            "engine": "PaperScope Original Question Intelligence",
            "pattern": pattern,
            "source_text_used_as_question": False,
            "original_scenario": True
        }
    }


def _conditional_probability(concept: str, difficulty: str, index: int):
    cases = [
        (
            "A factory has two production lines. Line A produces 60% of the items and has a defect rate of 2%. Line B produces 40% and has a defect rate of 5%. If a randomly selected item is known to be defective, which line is more likely to have produced it?",
            "Line B",
            ["Line A", "Both lines are equally likely", "It cannot be determined"],
            "Among defective items, Line B has the larger contribution because 40% × 5% is greater than 60% × 2%."
        ),
        (
            "In a college, 30% of students participate in a coding club. Among coding-club members, 80% have completed a data-structures course. What does the 80% represent?",
            "The conditional probability of completing the course given club membership",
            [
                "The probability of club membership given course completion",
                "The probability that a randomly selected student completes the course",
                "The probability that a student joins the club"
            ],
            "The condition is club membership, so the quantity describes the probability of course completion given that condition."
        ),
        (
            "A shipment contains products from two suppliers. Supplier X provides 70% of the products with a 1% failure rate, while Supplier Y provides 30% with a 4% failure rate. If an item is found to have failed, which supplier is relatively more likely to be responsible?",
            "Supplier Y",
            ["Supplier X", "Both suppliers equally", "Neither supplier"],
            "The failure contribution is 0.70 × 0.01 for X and 0.30 × 0.04 for Y; Y contributes more failed items."
        )
    ]

    q = cases[index % len(cases)]
    return _mcq(
        q[0], q[1], q[2], concept, difficulty, q[3],
        "real_world_conditional_probability"
    )


def _bayes(concept: str, difficulty: str, index: int):
    cases = [
        (
            "A disease affects 1% of a population. A screening test detects the disease in 95% of affected people and incorrectly flags 5% of healthy people. A person receives a positive result. Which statement is most accurate?",
            "The probability that the person actually has the disease is much lower than 95%",
            [
                "The probability is exactly 95%",
                "The person definitely has the disease",
                "The probability is exactly 5%"
            ],
            "Bayes' theorem combines the test characteristics with the low base rate. A positive result does not imply a 95% chance of disease."
        ),
        (
            "A fraud-detection system flags 10% of transactions. Historical data show that only 2% of all transactions are actually fraudulent. Why is the base fraud rate important when interpreting a flagged transaction?",
            "It is needed to update the probability of fraud after observing the flag",
            [
                "It guarantees every flagged transaction is fraudulent",
                "It replaces the detector's false-positive rate",
                "It makes conditional probabilities unnecessary"
            ],
            "Bayesian updating combines prior probability with the evidence and the likelihood of that evidence."
        )
    ]

    q = cases[index % len(cases)]
    return _mcq(
        q[0], q[1], q[2], concept, difficulty, q[3],
        "bayes_diagnostic_update"
    )


def _sampling(concept: str, difficulty: str, index: int):
    cases = [
        (
            "A national survey wants estimates separately for urban and rural households. The research team first divides households into urban and rural groups and then randomly samples households within each group. Which method is being used?",
            "Stratified sampling",
            ["Cluster sampling", "Convenience sampling", "Systematic sampling"],
            "The population is divided into strata and random samples are taken from each stratum."
        ),
        (
            "A student surveys only people standing outside the campus cafeteria to estimate the university-wide opinion about food services. What is the main concern?",
            "The sample may not represent the entire student population",
            ["The sample is automatically a census", "Randomization is guaranteed", "The population becomes smaller"],
            "Restricting respondents to one location can systematically exclude other students and create selection bias."
        ),
        (
            "A government agency wants a representative household sample but needs separate reliable estimates for several geographic regions. Which approach is most appropriate?",
            "Sample within predefined geographic strata",
            ["Survey only the largest city", "Survey volunteers who respond online", "Select households from one neighborhood"],
            "Geographic stratification can ensure that important regions are represented in the sample."
        )
    ]

    q = cases[index % len(cases)]
    return _mcq(
        q[0], q[1], q[2], concept, difficulty, q[3],
        "sampling_method_selection"
    )


def _quality(concept: str, difficulty: str, index: int):
    cases = [
        (
            "A national employment dashboard publishes accurate monthly figures, but the figures are released six months after the reference month. Which quality dimension is most directly affected?",
            "Timeliness",
            ["Accuracy", "Confidentiality", "Accessibility of raw records"],
            "The statistics may be accurate but are not available soon enough for timely use."
        ),
        (
            "Two official datasets measure the same economic indicator but use incompatible definitions, making their results difficult to compare. Which quality concern is most relevant?",
            "Coherence",
            ["Timeliness", "Processing speed", "Hardware reliability"],
            "Coherence concerns the consistency and comparability of statistical information."
        )
    ]

    q = cases[index % len(cases)]
    return _mcq(
        q[0], q[1], q[2], concept, difficulty, q[3],
        "quality_dimension_scenario"
    )


def _official_statistics(concept: str, difficulty: str, index: int):
    cases = [
        (
            "A government department needs monthly counts of business registrations. The information is already recorded as part of the department's registration system. Which source is most suitable?",
            "Administrative data",
            ["A new population census", "A laboratory experiment", "A convenience poll"],
            "Administrative records are created during routine government operations and can provide such information."
        ),
        (
            "A statistical agency needs detailed information about household income, employment and living conditions from a representative sample of households. Which source is most appropriate?",
            "A household sample survey",
            ["A computer benchmark", "A software log", "A network monitoring report"],
            "A household survey is designed to collect information directly from sampled households."
        )
    ]

    q = cases[index % len(cases)]
    return _mcq(
        q[0], q[1], q[2], concept, difficulty, q[3],
        "source_selection"
    )


def _process(concept: str, difficulty: str, index: int):
    cases = [
        (
            "A statistical agency has collected responses from a survey and must check errors, handle missing values and prepare the dataset before producing tables. Which stage is primarily involved?",
            "Data processing",
            ["Dissemination", "Questionnaire design only", "Public communication"],
            "Processing prepares collected data for analysis and statistical output."
        ),
        (
            "A statistical office has completed analysis and is making tables, indicators and reports available to users. Which stage is this?",
            "Dissemination",
            ["Sampling", "Data collection", "Editing raw responses"],
            "Dissemination is the stage in which statistical outputs are released to users."
        )
    ]

    q = cases[index % len(cases)]
    return _mcq(
        q[0], q[1], q[2], concept, difficulty, q[3],
        "production_stage_reasoning"
    )


def _data_analysis(concept: str, difficulty: str, index: int):
    cases = [
        (
            "An analyst observes that average household income increased while the median income changed very little. Which interpretation is most plausible?",
            "A relatively small number of high-income observations may have pulled the mean upward",
            [
                "The median must always be larger than the mean",
                "Every household must have received the same increase",
                "The data cannot contain outliers"
            ],
            "The mean is sensitive to extreme values, while the median is more resistant to them."
        ),
        (
            "A dataset contains one extremely large observation compared with all other values. Which measure is generally more resistant to the influence of that observation?",
            "Median",
            ["Mean", "Sum", "Range"],
            "The median is generally less affected by extreme observations than the mean."
        )
    ]

    q = cases[index % len(cases)]
    return _mcq(
        q[0], q[1], q[2], concept, difficulty, q[3],
        "interpretation_scenario"
    )


def _general(concept: str, difficulty: str, index: int):
    scenarios = [
        (
            f"A government analyst is applying {concept} to a new dataset. Which approach best demonstrates correct application of the concept?",
            f"Choose the method after identifying the conditions and assumptions relevant to {concept}",
            [
                "Apply the method without checking the data",
                "Ignore the purpose of the analysis",
                "Use the method simply because it was used previously"
            ],
            f"Correct application requires matching {concept} to the problem, data and assumptions."
        ),
        (
            f"A team is reviewing a statistical study involving {concept}. Which action would provide the strongest evidence that the concept has been applied appropriately?",
            "Check the assumptions, context and interpretation before accepting the result",
            [
                "Accept the result without reviewing the data",
                "Choose the answer with the largest number",
                "Ignore the study design"
            ],
            f"Sound statistical reasoning requires checking context, assumptions and interpretation."
        )
    ]

    q = scenarios[index % len(scenarios)]
    return _mcq(
        q[0], q[1], q[2], concept, difficulty, q[3],
        "general_application"
    )


_GENERATORS = {
    "probability": {
        "conditional probability": _conditional_probability,
        "bayes theorem": _bayes,
        "bayes' theorem": _bayes,
    },
    "sampling": _sampling,
    "data_quality": _quality,
    "official_statistics": _official_statistics,
    "statistical_process": _process,
    "data_analysis": _data_analysis,
}


def generate_original_questions(
    concepts: List[str],
    learner_profile: Dict[str, Any],
    number: int = 10,
    recent_questions: List[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:

    recent_questions = recent_questions or []
    recent = {_norm(q.get("question")) for q in recent_questions}

    results = []
    counters = {}

    for concept in concepts:
        if len(results) >= number:
            break

        concept = str(concept).strip()
        if not concept:
            continue

        family = _family(concept)
        difficulty = _difficulty(learner_profile, concept)

        if family == "probability":
            key = _norm(concept)
            generator = _GENERATORS["probability"].get(key)

            if generator is None:
                if "bayes" in key:
                    generator = _bayes
                else:
                    generator = _conditional_probability

        else:
            generator = _GENERATORS.get(family, _general)

        index = counters.get(_norm(concept), 0)
        counters[_norm(concept)] = index + 1

        try:
            q = generator(concept, difficulty, index)
        except Exception:
            q = _general(concept, difficulty, index)

        if _norm(q["question"]) in recent:
            continue

        q["mastery_before"] = round(_mastery(learner_profile, concept), 1)

        q["personalization"] = {
            "target_competency": concept,
            "current_mastery": q["mastery_before"],
            "recommended_difficulty": difficulty,
            "reason": (
                "LOW_MASTERY"
                if q["mastery_before"] < 50
                else "REINFORCEMENT"
            ),
            "exam_target": learner_profile.get("exam_target")
        }

        results.append(q)

    return results[:number]
