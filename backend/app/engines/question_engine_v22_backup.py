import random
import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# PaperScope Question Intelligence Engine v4
# ============================================================
#
# Design principles:
#
# 1. Questions are generated from evidence in the material.
# 2. Concepts are selected using ML-based document similarity.
# 3. Difficulty is derived from evidence complexity.
# 4. We do not repeat one sentence just to reach N questions.
# 5. Distractors are selected from semantically related concepts.
# 6. The engine supports lectures/notes as learning material,
#    not just PYQs.
#
# ============================================================


STOPWORDS = {
    "about", "after", "again", "against", "also", "because",
    "before", "being", "between", "could", "during", "each",
    "from", "further", "have", "having", "into", "more",
    "most", "other", "over", "same", "should", "some",
    "such", "than", "that", "their", "there", "these",
    "they", "this", "those", "through", "under", "very",
    "were", "what", "when", "where", "which", "while",
    "with", "would", "your", "ours", "ourselves", "the",
    "and", "for", "are", "was", "were", "has", "had",
    "not", "but", "you", "from", "its"
}


def clean_text(text):
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def normalize(value):
    return re.sub(r"[^a-z0-9 ]", "", value.lower()).strip()


def split_sentences(text):
    text = clean_text(text)

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    return [
        clean_text(sentence)
        for sentence in sentences
        if len(clean_text(sentence).split()) >= 6
    ]


def tokenize(text):
    words = re.findall(
        r"\b[a-zA-Z][a-zA-Z\-]{2,}\b",
        text.lower()
    )

    return [
        word
        for word in words
        if word not in STOPWORDS
    ]


# ============================================================
# ML EVIDENCE MODEL
# ============================================================

class EvidenceModel:

    def __init__(self, sentences):
        self.sentences = sentences

        if not sentences:
            self.vectorizer = None
            self.matrix = None
            return

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
        )

        self.matrix = self.vectorizer.fit_transform(
            sentences
        )

    def similarity(self, sentence_a, sentence_b):
        if not self.vectorizer:
            return 0.0

        vectors = self.vectorizer.transform(
            [sentence_a, sentence_b]
        )

        return float(
            cosine_similarity(
                vectors[0:1],
                vectors[1:2]
            )[0][0]
        )

    def related_sentences(self, seed_sentence):
        if not self.vectorizer:
            return []

        seed = self.vectorizer.transform(
            [seed_sentence]
        )

        similarities = cosine_similarity(
            seed,
            self.matrix
        )[0]

        ranked = sorted(
            enumerate(similarities),
            key=lambda item: item[1],
            reverse=True
        )

        return [
            {
                "sentence_index": index,
                "sentence": self.sentences[index],
                "similarity": round(float(score), 4)
            }
            for index, score in ranked
        ]


# ============================================================
# CONCEPT DISCOVERY
# ============================================================

def is_heading_sentence(sentence):
    """
    Detect short title/heading-like sentences.

    Headings should help identify the topic, but should not become
    concepts themselves or act as evidence for questions.
    """
    words = sentence.strip().split()

    if len(words) <= 8 and re.match(
        r"^(lecture|chapter|unit|module|topic|lesson)\b",
        sentence.strip(),
        re.IGNORECASE,
    ):
        return True

    return False


def clean_candidate_phrase(phrase):
    """
    Normalize a candidate concept phrase and reject obvious noise.
    """
    phrase = re.sub(r"\s+", " ", phrase.lower()).strip()

    words = phrase.split()

    if not words:
        return None

    if len(words) > 4:
        return None

    if any(
        word in STOPWORDS
        for word in words
    ):
        # Allow meaningful phrases such as
        # "official statistics", but reject phrases beginning
        # or ending with common function words.
        if words[0] in STOPWORDS or words[-1] in STOPWORDS:
            return None

    if len(set(words)) != len(words):
        return None

    if any(
        len(word) < 3
        for word in words
    ):
        return None

    # Reject generic lecture/title vocabulary.
    GENERIC = {
        "lecture",
        "chapter",
        "unit",
        "module",
        "topic",
        "lesson",
        "introduction",
        "overview",
        "summary",
        "example",
        "examples",
        "following",
        "following material",
    }

    if phrase in GENERIC:
        return None

    return phrase


def extract_meaningful_phrases(sentence):
    """
    Extract candidate educational phrases from a sentence.

    Priority:
      1. Explicit definition phrases:
         'X are ...'
         'X is ...'
         'X refers to ...'
         'X means ...'
      2. Noun-like bigrams.
      3. Important single terms.

    This intentionally avoids accepting arbitrary TF-IDF
    n-grams as concepts.
    """
    candidates = []

    lowered = sentence.lower()

    # --------------------------------------------------------
    # Definition-pattern extraction
    # --------------------------------------------------------
    definition_patterns = [
        r"\b([a-zA-Z][a-zA-Z-]*(?:\s+[a-zA-Z][a-zA-Z-]*){0,2})\s+"
        r"(?:is|are|refers to|means|denotes|is defined as)\b",

        r"\b([a-zA-Z][a-zA-Z-]*(?:\s+[a-zA-Z][a-zA-Z-]*){0,2})\s+"
        r"(?:consists of|includes|comprises)\b",
    ]

    for pattern in definition_patterns:
        for match in re.finditer(pattern, lowered):
            phrase = clean_candidate_phrase(match.group(1))

            if phrase:
                candidates.append(phrase)

    # --------------------------------------------------------
    # Noun-like bigrams
    # --------------------------------------------------------
    words = re.findall(
        r"\b[a-zA-Z][a-zA-Z-]{2,}\b",
        lowered
    )

    filtered = [
        word
        for word in words
        if word not in STOPWORDS
    ]

    for i in range(len(filtered) - 1):
        phrase = clean_candidate_phrase(
            f"{filtered[i]} {filtered[i + 1]}"
        )

        if phrase:
            candidates.append(phrase)

    # --------------------------------------------------------
    # Meaningful single terms
    # --------------------------------------------------------
    for word in filtered:
        phrase = clean_candidate_phrase(word)

        if phrase:
            candidates.append(phrase)

    return candidates



def discover_concepts(sentences, limit=20):
    """
    PaperScope Concept Intelligence v22.

    Discover genuine educational concepts from learning material.

    Rules:
      - Prefer meaningful noun phrases.
      - Preserve explicit definition subjects.
      - Reject isolated verbs/adjectives/descriptors.
      - Reject words that are merely components of a stronger phrase.
      - Prefer domain nouns and domain noun phrases.
      - Never treat lecture headings as concepts.
    """

    if not sentences:
        return []

    BAD_WORDS = {
        "produced", "produce", "produces",
        "describe", "describes", "described",
        "discuss", "discussed",
        "refers", "means", "denotes",
        "using", "used",
        "following", "according", "based",
        "called", "known",
        "provides", "provide",
        "includes", "include",
        "shows", "shown",
        "is", "are", "was", "were", "be",
        "being", "been", "and", "or", "but",
        "to", "of", "for", "with", "from", "by",
        "the", "a", "an"
    }

    DESCRIPTOR_WORDS = {
        "economic",
        "demographic",
        "social",
        "official",
        "national",
        "public",
        "statistical",
    }

    DOMAIN_NOUNS = {
        "statistics",
        "agencies",
        "conditions",
        "data",
        "government",
        "population",
        "employment",
        "income",
        "education",
        "health",
        "development",
        "survey",
        "surveys",
        "census",
        "indicator",
        "indicators",
        "measurement",
        "method",
        "methods",
        "system",
        "systems",
        "policy",
        "policies",
        "economy",
        "information",
        "research",
        "sample",
        "sampling",
        "variable",
        "variables",
        "dataset",
        "datasets",
        "institution",
        "institutions",
        "organization",
        "organizations",
    }

    def valid_phrase(phrase):
        phrase = re.sub(r"\s+", " ", phrase.lower()).strip()
        words = phrase.split()

        if not phrase:
            return False

        if len(words) > 4:
            return False

        if len(set(words)) != len(words):
            return False

        if any(len(word) < 3 for word in words):
            return False

        if any(word in BAD_WORDS for word in words):
            return False

        # A descriptor alone is not a concept.
        if len(words) == 1 and words[0] in DESCRIPTOR_WORDS:
            return False

        # Single-word concepts must be recognised domain nouns.
        if len(words) == 1 and words[0] not in DOMAIN_NOUNS:
            return False

        # A two-word phrase made entirely from descriptors is noise.
        if len(words) == 2 and all(
            word in DESCRIPTOR_WORDS
            for word in words
        ):
            return False

        return True

    candidates = []

    for sentence in sentences:

        if is_heading_sentence(sentence):
            continue

        lowered = sentence.lower()

        # ----------------------------------------------------
        # 1. Explicit definition subjects
        # ----------------------------------------------------
        definition_patterns = [
            r"\b([a-zA-Z][a-zA-Z-]*(?:\s+[a-zA-Z][a-zA-Z-]*){0,2})\s+"
            r"(?:is|are|refers to|means|denotes|is defined as)\b",

            r"\b([a-zA-Z][a-zA-Z-]*(?:\s+[a-zA-Z][a-zA-Z-]*){0,2})\s+"
            r"(?:consists of|includes|comprises)\b",
        ]

        for pattern in definition_patterns:
            for match in re.finditer(pattern, lowered):
                phrase = match.group(1).strip()

                if valid_phrase(phrase):
                    candidates.append(phrase)

        # ----------------------------------------------------
        # 2. Domain noun phrases
        #
        # Preserve adjective + domain noun combinations such
        # as:
        #   official statistics
        #   government agencies
        #   social conditions
        #   demographic conditions
        # ----------------------------------------------------
        words = re.findall(
            r"\b[a-zA-Z][a-zA-Z-]{2,}\b",
            lowered
        )

        for i in range(len(words) - 1):

            first = words[i]
            second = words[i + 1]

            # adjective + domain noun
            if (
                first in DESCRIPTOR_WORDS
                and second in DOMAIN_NOUNS
            ):
                phrase = f"{first} {second}"

                if valid_phrase(phrase):
                    candidates.append(phrase)

            # domain noun + domain noun
            elif (
                first in DOMAIN_NOUNS
                and second in DOMAIN_NOUNS
            ):
                phrase = f"{first} {second}"

                if valid_phrase(phrase):
                    candidates.append(phrase)

        # ----------------------------------------------------
        # 3. Important domain nouns
        # ----------------------------------------------------
        for word in words:

            if word in DOMAIN_NOUNS and valid_phrase(word):
                candidates.append(word)

    # --------------------------------------------------------
    # Frequency ranking
    # --------------------------------------------------------
    frequency = {}

    for candidate in candidates:
        frequency[candidate] = frequency.get(candidate, 0) + 1

    ranked = sorted(
        frequency.items(),
        key=lambda item: (
            item[1],
            len(item[0].split()),
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # Remove weaker concepts contained inside stronger phrases.
    #
    # Example:
    #   official statistics  -> keep
    #   statistics            -> remove
    #
    # But:
    #   government agencies  -> keep
    #   agencies             -> remove
    # --------------------------------------------------------
    selected = []

    for concept, freq in ranked:

        concept_words = set(concept.split())

        contained = False

        for existing in selected:

            existing_words = set(existing.split())

            if (
                concept_words < existing_words
                and concept in existing
            ):
                contained = True
                break

        if contained:
            continue

        selected.append(concept)

        if len(selected) >= limit:
            break

    # build_concept_analysis() expects concept records rather than
    # raw strings. Preserve the v22 filtering while returning the
    # existing engine-compatible structure.
    results = []

    for concept in selected:
        results.append({
            "concept": concept,
            "frequency": frequency.get(concept, 1),
            "evidence": [
                sentence
                for sentence in sentences
                if normalize(concept) in normalize(sentence)
            ],
        })

    return results


def analyze_concept(
    concept,
    sentences,
    evidence_model,
    ml_score=0.0,
):
    """
    Analyze one discovered educational concept.

    Restores the concept-analysis layer used by
    build_concept_analysis().
    """

    concept_normalized = normalize(concept)

    frequency = 0
    units = []
    evidence = []

    for index, sentence in enumerate(sentences):

        sentence_normalized = normalize(sentence)

        if concept_normalized not in sentence_normalized:
            continue

        frequency += sentence_normalized.count(
            concept_normalized
        )

        units.append(index)

        evidence.append(sentence)

    if not evidence:
        return None

    unit_count = len(
        set(units)
    )

    total_units = max(
        len(sentences),
        1
    )

    coverage = (
        unit_count / total_units
    ) * 100

    # Word-share measures how strongly the concept is represented
    # in the material without allowing it to dominate importance.
    concept_word_count = len(
        concept_normalized.split()
    )

    total_words = max(
        sum(
            len(sentence.split())
            for sentence in sentences
        ),
        1
    )

    occurrences = max(
        frequency,
        1
    )

    word_share = min(
        (
            occurrences
            * concept_word_count
            / total_words
        ) * 100,
        100.0
    )

    # Importance combines recurrence and coverage.
    importance = (
        frequency * 10
        + coverage * 0.5
        + word_share * 0.2
    )

    importance = min(
        round(importance, 1),
        100.0
    )

    return {
        "concept": concept,
        "frequency": frequency,
        "units": sorted(set(units)),
        "unit_count": unit_count,
        "coverage": round(coverage, 1),
        "word_share": round(word_share, 1),
        "importance": importance,
        "evidence": evidence,
    }


def build_concept_analysis(
    text,
    existing_analysis=None
):

    sentences = split_sentences(text)

    if not sentences:
        return {
            "concepts": [],
            "sub_concepts": [],
        }

    evidence_model = EvidenceModel(
        sentences
    )

    discovered = discover_concepts(
        sentences,
        limit=25
    )

    concepts = []

    for item in discovered:

        result = analyze_concept(
            concept=item["concept"],
            sentences=sentences,
            evidence_model=evidence_model,
            ml_score=item.get(
                "ml_score",
                0.0
            ),
        )

        if result:
            concepts.append(result)

    # --------------------------------------------------------
    # PaperScope Topic Intelligence
    # --------------------------------------------------------
    # Assign every discovered concept to a meaningful topic
    # before questions and competency analysis are generated.
    #
    # This is intentionally lightweight and deterministic so
    # the topic layer remains explainable and stable.
    topic_rules = {
        "Official Statistics": [
            "official statistics",
            "government agencies",
            "government agency",
            "economic conditions",
            "social conditions",
            "demographic",
            "official data",
        ],
        "Data Quality": [
            "data quality",
            "accuracy",
            "reliability",
            "validity",
            "completeness",
            "consistency",
        ],
    }

    for item in concepts:
        concept_name = normalize(
            item.get("concept", "")
        )

        evidence_text = normalize(
            " ".join(
                item.get("evidence", [])
            )
        )

        combined_text = (
            concept_name
            + " "
            + evidence_text
        )

        assigned_topic = None

        for topic, keywords in topic_rules.items():
            if any(
                normalize(keyword) in combined_text
                for keyword in keywords
            ):
                assigned_topic = topic
                break

        if assigned_topic:
            item["topic"] = assigned_topic
        else:
            item["topic"] = "General Concepts"

    # Remove near-duplicate concepts.
    unique = []
    seen = set()

    for item in sorted(
        concepts,
        key=lambda x: x["importance"],
        reverse=True
    ):

        key = normalize(
            item["concept"]
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    # Convert importance to normalized material weightage.
    total_importance = sum(
        item["importance"]
        for item in unique
    )

    for item in unique:

        if total_importance:
            item["weightage"] = round(
                (
                    item["importance"]
                    / total_importance
                ) * 100,
                2
            )
        else:
            item["weightage"] = 0.0

    # Basic relationship graph.
    #
    # Concepts appearing in similar sentences are treated as
    # candidate sub-concepts.
    sub_concepts = []

    for parent in unique[:10]:

        related = []

        parent_evidence = " ".join(
            parent["evidence"]
        )

        for child in unique:

            if child is parent:
                continue

            similarity = evidence_model.similarity(
                parent_evidence,
                " ".join(child["evidence"])
            )

            if similarity >= 0.10:
                related.append({
                    "concept": child["concept"],
                    "similarity": round(
                        similarity,
                        3
                    ),
                })

        related = sorted(
            related,
            key=lambda x: x["similarity"],
            reverse=True
        )[:5]

        sub_concepts.append({
            "concept": parent["concept"],
            "sub_concepts": related,
        })

    return {
        "concepts": unique,
        "sub_concepts": sub_concepts,
    }


# ============================================================
# DIFFICULTY
# ============================================================

def derive_difficulty(
    concept_data,
    evidence
):

    importance = float(
        concept_data.get(
            "importance",
            0
        )
    )

    coverage = float(
        concept_data.get(
            "coverage",
            0
        )
    )

    words = len(
        evidence.split()
    )

    has_definition = bool(
        re.search(
            r"\b(is|are|means|refers to|defined as)\b",
            evidence,
            re.I
        )
    )

    has_relation = bool(
        re.search(
            r"\b(because|therefore|however|whereas|while|leads to|results in)\b",
            evidence,
            re.I
        )
    )

    if has_relation or words >= 35:
        return "hard"

    if has_definition or (
        importance >= 35
        and coverage >= 20
    ):
        return "medium"

    return "easy"


# ============================================================
# QUESTION STRATEGY
# ============================================================

def select_question_type(
    evidence,
    difficulty,
    concept=None,
):
    """
    Select a question type using both the evidence and the
    specific concept being tested.

    A definition trigger such as "is" or "are" should only
    produce a definition question when the concept itself
    participates in that definition.
    """

    lowered = evidence.lower()
    concept_normalized = normalize(
        str(concept or "")
    )

    # --------------------------------------------------------
    # Definition detection
    # --------------------------------------------------------
    definition_match = re.search(
        r"\\b(is|are|refers to|defined as|means|denotes)\\b",
        lowered,
    )

    if definition_match and concept_normalized:

        # Check whether the concept occurs before the
        # definition verb. This avoids treating a concept
        # mentioned later in the sentence as if it were
        # being defined.
        verb_start = definition_match.start()

        before_definition = normalize(
            lowered[:verb_start]
        )

        if concept_normalized in before_definition:
            return "definition"

    # --------------------------------------------------------
    # Relationship / understanding
    # --------------------------------------------------------
    if re.search(
        r"\\b(because|therefore|leads to|results in|"
        r"due to|causes|depends on)\\b",
        lowered,
    ):
        return "understanding"

    # --------------------------------------------------------
    # Purpose / usage
    # --------------------------------------------------------
    if re.search(
        r"\\b(used to|used for|helps to|"
        r"serves to|designed to)\\b",
        lowered,
    ):
        return "understanding"

    # --------------------------------------------------------
    # Hard evidence
    # --------------------------------------------------------
    if difficulty == "hard":
        return "reasoning"

    return "identification"


def question_text(
    concept,
    question_type
):

    if question_type == "definition":
        return (
            f"What does {concept} refer to "
            "according to the learning material?"
        )

    if question_type == "understanding":
        return (
            f"Which statement best explains "
            f"{concept} based on the learning material?"
        )

    if question_type == "reasoning":
        return (
            f"Which interpretation is most consistent "
            f"with the material on {concept}?"
        )

    return (
        f"Which statement correctly identifies "
        f"{concept}?"
    )


# ============================================================
# DISTRACTOR ENGINE
# ============================================================

def build_distractors(
    concept_data,
    concept_pool,
    evidence_model
):

    concept = concept_data["concept"]

    candidates = []

    target_evidence = " ".join(
        concept_data.get(
            "evidence",
            []
        )
    )

    for item in concept_pool:

        if item is concept_data:
            continue

        candidate = item.get(
            "concept",
            ""
        )

        if not candidate:
            continue

        if normalize(candidate) == normalize(
            concept
        ):
            continue

        candidate_evidence = " ".join(
            item.get(
                "evidence",
                []
            )
        )

        similarity = evidence_model.similarity(
            target_evidence,
            candidate_evidence
        )

        # We want related concepts, but not the answer itself.
        candidates.append(
            (
                candidate,
                similarity
            )
        )

    candidates.sort(
        key=lambda x: x[1],
        reverse=True
    )

    selected = []

    for candidate, similarity in candidates:

        if normalize(candidate) in {
            normalize(x)
            for x in selected
        }:
            continue

        selected.append(candidate)

        if len(selected) == 3:
            break

    return selected


# ============================================================
# QUESTION QUALITY CHECK
# ============================================================

def validate_question(
    question,
    evidence
):

    if not question:
        return False

    if len(
        question.get("options", [])
    ) != 4:
        return False

    options = [
        normalize(option)
        for option in question["options"]
    ]

    if len(set(options)) != 4:
        return False

    answer = question.get("answer")

    if not isinstance(answer, int):
        return False

    if answer < 0 or answer >= 4:
        return False

    if not evidence:
        return False

    return True


# ============================================================
# CREATE QUESTION
# ============================================================

def select_evidence(concept, sentences, evidence_model=None):
    """Return the strongest evidence sentences for a concept.

    Accepts either:
    - plain sentence strings
    - evidence dictionaries containing a 'sentence' field
    """

    if not sentences:
        return []

    # Normalize incoming evidence into:
    # [(original_index, sentence_text)]
    normalized_sentences = []

    for index, item in enumerate(sentences):
        if isinstance(item, dict):
            sentence = item.get("sentence", "")
            sentence_index = item.get("sentence_index", index)
        else:
            sentence = str(item)
            sentence_index = index

        if sentence:
            normalized_sentences.append(
                (sentence_index, sentence)
            )

    if not normalized_sentences:
        return []

    concept_normalized = normalize(str(concept))

    # --------------------------------------------------------
    # 1. Direct phrase match
    # --------------------------------------------------------
    direct = []

    for sentence_index, sentence in normalized_sentences:
        normalized_sentence = normalize(sentence)

        if (
            concept_normalized
            and concept_normalized in normalized_sentence
        ):
            direct.append({
                "sentence_index": sentence_index,
                "sentence": sentence,
                "score": 1.0,
            })

    if direct:
        return direct[:3]

    # --------------------------------------------------------
    # 2. Token-overlap fallback
    # --------------------------------------------------------
    concept_tokens = {
        token
        for token in concept_normalized.split()
        if len(token) >= 3
    }

    candidates = []

    for sentence_index, sentence in normalized_sentences:
        sentence_tokens = set(
            normalize(sentence).split()
        )

        overlap = len(
            concept_tokens & sentence_tokens
        )

        if overlap:
            score = overlap / max(
                len(concept_tokens),
                1
            )

            candidates.append({
                "sentence_index": sentence_index,
                "sentence": sentence,
                "score": float(score),
            })

    if candidates:
        candidates.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return candidates[:3]

    # --------------------------------------------------------
    # 3. TF-IDF similarity fallback
    # --------------------------------------------------------
    if evidence_model is not None:
        try:
            ranked = evidence_model.related_sentences(
                str(concept)
            )

            return [
                {
                    "sentence_index": item["sentence_index"],
                    "sentence": item["sentence"],
                    "score": item["similarity"],
                }
                for item in ranked[:3]
            ]

        except Exception:
            pass

    return []







def create_question(
    concept_data,
    sentences,
    concept_pool,
    index,
    used_questions=None,
    used_evidence=None,
):
    """
    PaperScope Question Intelligence Engine v16.

    Evidence-first MCQ generation.

    The generator does NOT contain subject-specific questions.
    It extracts relationships directly from the learning material.

    Supported evidence patterns:
      - definition
      - representation
      - purpose
      - components/lists
      - relationship
      - identification

    Every question must have:
      - one source-grounded answer
      - three semantically compatible distractors
      - four unique options
    """

    used_questions = used_questions or set()
    used_evidence = used_evidence or set()

    concept = str(
        concept_data.get("concept", "")
    ).strip()

    if not concept:
        return None

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def clean(value):
        return re.sub(
            r"\s+",
            " ",
            str(value).strip(" .,:;")
        )

    def key(value):
        return normalize(clean(value))

    def unique(values):
        result = []
        seen = set()

        for value in values:
            value = clean(value)
            k = key(value)

            if not value or not k or k in seen:
                continue

            seen.add(k)
            result.append(value)

        return result

    def sentence_text(item):
        if isinstance(item, dict):
            return clean(item.get("sentence", ""))

        return clean(item)

    # ---------------------------------------------------------
    # Gather source evidence
    # ---------------------------------------------------------

    evidence_items = []

    # Prefer concept-specific evidence.
    for item in concept_data.get("evidence", []):
        sentence = sentence_text(item)

        if sentence:
            evidence_items.append(sentence)

    # Fall back to direct evidence search.
    if not evidence_items:
        discovered = select_evidence(
            concept,
            sentences
        )

        for item in discovered:
            sentence = sentence_text(item)

            if sentence:
                evidence_items.append(sentence)

    evidence_items = unique(evidence_items)

    if not evidence_items:
        return None

    # Prefer unused evidence.
    fresh = [
        item
        for item in evidence_items
        if key(item) not in used_evidence
    ]

    if fresh:
        evidence_items = fresh + [
            item
            for item in evidence_items
            if key(item) in used_evidence
        ]

    # ---------------------------------------------------------
    # Concept pool
    # ---------------------------------------------------------

    pool = []

    for item in concept_pool:

        candidate = (
            item.get("concept")
            if isinstance(item, dict)
            else str(item)
        )

        candidate = clean(candidate)

        if not candidate:
            continue

        if key(candidate) == key(concept):
            continue

        if len(candidate.split()) > 6:
            continue

        pool.append(candidate)

    pool = unique(pool)

    # ---------------------------------------------------------
    # Extract compatible answer alternatives.
    #
    # These are source concepts, not fabricated subject facts.
    # ---------------------------------------------------------

    def concept_alternatives(answer):
        answer_key = key(answer)

        candidates = []

        for candidate in pool:

            if key(candidate) == answer_key:
                continue

            # Don't use a fragment of the answer.
            if (
                key(candidate) in answer_key
                or answer_key in key(candidate)
            ):
                continue

            candidates.append(candidate)

        return unique(candidates)

    # ---------------------------------------------------------
    # Controlled semantic fallback.
    #
    # Used only when the material itself contains fewer than
    # three suitable concepts.
    #
    # The fallback is generic and category-preserving rather
    # than subject-specific.
    # ---------------------------------------------------------

    def semantic_fallback(answer, question_type):

        if question_type == "representation":
            return [
                "flowchart",
                "database schema",
                "network diagram",
            ]

        if question_type == "purpose":
            return [
                "data storage",
                "system monitoring",
                "user authentication",
            ]

        if question_type == "components":
            return [
                "alternative mathematical laws",
                "unrelated physical laws",
                "general programming operations",
            ]

        if question_type == "relationship":
            return [
                "measurement",
                "classification",
                "visualization",
            ]

        if question_type == "definition":
            return [
                "a measurement method",
                "a storage structure",
                "a communication protocol",
            ]

        return [
            "measurement",
            "classification",
            "visualization",
        ]

    # ---------------------------------------------------------
    # Build final MCQ
    # ---------------------------------------------------------

    def build(
        question,
        answer,
        distractors,
        question_type,
        evidence,
    ):

        question = clean(question)
        answer = clean(answer)
        distractors = unique(distractors)

        if not question or not answer:
            return None

        # Exactly three distractors.
        final_distractors = []

        for candidate in distractors:

            if key(candidate) == key(answer):
                continue

            if key(candidate) in {
                key(x)
                for x in final_distractors
            }:
                continue

            final_distractors.append(candidate)

            if len(final_distractors) == 3:
                break

        if len(final_distractors) < 3:
            return None

        options = [
            answer,
            *final_distractors,
        ]

        options = unique(options)

        if len(options) != 4:
            return None

        question_key = key(question)

        if question_key in used_questions:
            return None

        # Reject questions that are essentially identical.
        question_tokens = set(
            tokenize(question)
        )

        if question_tokens:
            for existing in used_questions:
                existing_tokens = set(
                    tokenize(existing)
                )

                if not existing_tokens:
                    continue

                similarity = (
                    len(question_tokens & existing_tokens)
                    /
                    max(
                        len(question_tokens | existing_tokens),
                        1,
                    )
                )

                if similarity >= 0.72:
                    return None

        rng = random.Random(
            7919 * index
        )

        rng.shuffle(options)

        answer_index = options.index(answer)

        difficulty = derive_difficulty(
            concept_data,
            evidence,
        )

        return {
            "id": f"PS-Q{index:04d}",
            "topic": concept_data.get(
                "topic",
                "General Concepts"
            ),
            "concept": concept,
            "difficulty": difficulty,
            "question_type": question_type,
            "question": question,
            "options": options,
            "answer": answer_index,
            "explanation": (
                f"The answer is directly supported by "
                f"the source evidence: {evidence}"
            ),
            "source_sentence": [
                {
                    "sentence": evidence,
                    "score": 1.0,
                }
            ],
        }

    # ---------------------------------------------------------
    # Analyze each evidence sentence.
    # ---------------------------------------------------------

    for evidence in evidence_items:

        lowered = evidence.lower()
        normalized_evidence = normalize(evidence)

        # =====================================================
        # 1. DEFINITION
        # =====================================================

        definition_patterns = [
            r"\b(.{2,100}?)\s+is\s+(.{5,220})",
            r"\b(.{2,100}?)\s+are\s+(.{5,220})",
            r"\b(.{2,100}?)\s+refers to\s+(.{5,220})",
            r"\b(.{2,100}?)\s+means\s+(.{5,220})",
            r"\b(.{2,100}?)\s+is defined as\s+(.{5,220})",
        ]

        for pattern in definition_patterns:

            match = re.search(
                pattern,
                evidence,
                re.I
            )

            if not match:
                continue

            subject = clean(match.group(1))
            definition = clean(match.group(2))

            if key(concept) not in key(subject):
                continue

            definition = re.split(
                r"\b(?:however|although|while|but)\b",
                definition,
                maxsplit=1,
                flags=re.I,
            )[0].strip()

            distractors = concept_alternatives(
                definition
            )

            if len(distractors) < 3:
                distractors.extend(
                    semantic_fallback(
                        definition,
                        "definition"
                    )
                )

            result = build(
                f"Which statement best defines {concept}?",
                definition,
                distractors,
                "definition",
                evidence,
            )

            if result:
                return result

        # =====================================================
        # 2. REPRESENTATION
        # =====================================================

        representation_patterns = [
            r"\bcan be represented using\s+(.+?)[.!?]?$",
            r"\bis represented using\s+(.+?)[.!?]?$",
            r"\bis represented by\s+(.+?)[.!?]?$",
        ]

        for pattern in representation_patterns:

            match = re.search(
                pattern,
                evidence,
                re.I,
            )

            if not match:
                continue

            prefix = normalize(
                evidence[:match.start()]
            )

            if key(concept) not in prefix:
                continue

            representation = clean(
                match.group(1)
            )

            distractors = concept_alternatives(
                representation
            )

            if len(distractors) < 3:
                distractors.extend(
                    semantic_fallback(
                        representation,
                        "representation"
                    )
                )

            result = build(
                f"How can {concept} be represented?",
                representation,
                distractors,
                "representation",
                evidence,
            )

            if result:
                return result

        # =====================================================
        # 3. PURPOSE / APPLICATION
        # =====================================================

        purpose_match = re.search(
            r"\b(used to|used for|helps to|serves to|"
            r"designed to)\s+(.+?)[.!?]?$",
            evidence,
            re.I,
        )

        if purpose_match:

            prefix = normalize(
                evidence[:purpose_match.start()]
            )

            if key(concept) in prefix:

                purpose = clean(
                    purpose_match.group(2)
                )

                distractors = concept_alternatives(
                    purpose
                )

                if len(distractors) < 3:
                    distractors.extend(
                        semantic_fallback(
                            purpose,
                            "purpose"
                        )
                    )

                result = build(
                    f"What is {concept} used for?",
                    purpose,
                    distractors,
                    "purpose",
                    evidence,
                )

                if result:
                    return result

        # =====================================================
        # 4. COMPONENT / LIST
        # =====================================================

        component_match = re.search(
            r"\b(includes|include|consists of|comprises)\s+"
            r"(.+?)[.!?]?$",
            evidence,
            re.I,
        )

        if component_match:

            prefix = normalize(
                evidence[:component_match.start()]
            )

            if key(concept) in prefix:

                components = clean(
                    component_match.group(2)
                )

                distractors = concept_alternatives(
                    components
                )

                if len(distractors) < 3:
                    distractors.extend(
                        semantic_fallback(
                            components,
                            "components"
                        )
                    )

                result = build(
                    f"Which set of elements is associated with {concept}?",
                    components,
                    distractors,
                    "components",
                    evidence,
                )

                if result:
                    return result

        # =====================================================
        # 5. RELATIONSHIP
        # =====================================================

        relation_patterns = [
            r"^(.+?)\s+(combines|combine)\s+(.+?)\s+"
            r"(?:using|through|with)\s+(.+?)[.!?]?$",

            r"^(.+?)\s+(uses|use)\s+(.+?)[.!?]?$",

            r"^(.+?)\s+(produces|produce)\s+(.+?)[.!?]?$",

            r"^(.+?)\s+(requires|require)\s+(.+?)[.!?]?$",
        ]

        for pattern in relation_patterns:

            match = re.search(
                pattern,
                evidence,
                re.I,
            )

            if not match:
                continue

            subject = clean(
                match.group(1)
            )

            if key(concept) != key(subject):
                continue

            relation = match.group(2)
            target = clean(
                match.group(3)
            )

            distractors = concept_alternatives(
                target
            )

            if len(distractors) < 3:
                distractors.extend(
                    semantic_fallback(
                        target,
                        "relationship"
                    )
                )

            if relation.lower() in {
                "uses",
                "use",
            }:
                question = (
                    f"What does {concept} use?"
                )

            elif relation.lower() in {
                "produces",
                "produce",
            }:
                question = (
                    f"What does {concept} produce?"
                )

            elif relation.lower() in {
                "requires",
                "require",
            }:
                question = (
                    f"What does {concept} require?"
                )

            else:
                question = (
                    f"What does {concept} combine?"
                )

            result = build(
                question,
                target,
                distractors,
                "relationship",
                evidence,
            )

            if result:
                return result

    # ---------------------------------------------------------
    # No safe evidence-based question.
    # ---------------------------------------------------------

    return None




def generate_evidence_candidates(
    concept_data,
    sentences,
    concept_pool,
    index,
):
    """
    Step 19:
    Generate multiple evidence-grounded question candidates
    from the same concept/evidence instead of accepting only
    the first available question form.

    No external knowledge is introduced.
    """

    concept = str(
        concept_data.get("concept", "")
    ).strip()

    if not concept:
        return []

    evidence = select_evidence(
        concept,
        sentences
    )

    if not evidence:
        return []

    evidence_items = []

    for item in evidence:
        if isinstance(item, dict):
            sentence = str(
                item.get("sentence", "")
            ).strip()
        else:
            sentence = str(item).strip()

        if sentence:
            evidence_items.append(sentence)

    if not evidence_items:
        return []

    candidates = []

    def add(
        question,
        correct,
        distractors,
        question_type,
    ):
        question = clean_text(question)
        correct = clean_text(correct)

        if not question or not correct:
            return

        distractors = [
            clean_text(x)
            for x in distractors
            if clean_text(x)
        ]

        if len(distractors) < 3:
            return

        candidates.append({
            "question": question,
            "correct": correct,
            "distractors": distractors[:3],
            "question_type": question_type,
            "evidence": evidence_items,
        })

    for evidence_text in evidence_items:

        lowered = evidence_text.lower()
        concept_normalized = normalize(concept)

        # -----------------------------------------------------
        # Representation
        # -----------------------------------------------------

        match = re.search(
            r"\bcan be represented using\s+(.+?)[.!?]?$",
            evidence_text,
            re.I
        )

        if match and concept_normalized in normalize(
            evidence_text[:match.start()]
        ):
            representation = clean_text(
                match.group(1)
            )

            add(
                f"How can {concept} be represented?",
                representation,
                [
                    "a database table",
                    "a flowchart",
                    "a network diagram",
                ],
                "representation",
            )

            add(
                f"Which representation is associated with {concept}?",
                representation,
                [
                    "a database schema",
                    "a bar chart",
                    "a process diagram",
                ],
                "representation",
            )

        # -----------------------------------------------------
        # Combines / uses
        # -----------------------------------------------------

        match = re.search(
            r"^(.+?)\s+(combines|combine)\s+(.+?)\s+"
            r"(?:using|through|with)\s+(.+?)[.!?]?$",
            evidence_text,
            re.I
        )

        if match and concept_normalized == normalize(
            match.group(1)
        ):
            target = clean_text(match.group(3))
            mechanism = clean_text(match.group(4))

            add(
                f"What does {concept} combine?",
                target,
                [
                    "statistical samples",
                    "database records",
                    "physical measurements",
                ],
                "relationship",
            )

            add(
                f"What does {concept} combine using {mechanism}?",
                target,
                [
                    "statistical samples",
                    "database records",
                    "physical measurements",
                ],
                "relationship",
            )

        # -----------------------------------------------------
        # Basic operations / components
        # -----------------------------------------------------

        match = re.search(
            r"^(.+?)\s+(?:are|is)\s+(.+?)[.!?]?$",
            evidence_text,
            re.I
        )

        if match:

            subject = clean_text(
                match.group(1)
            )

            predicate = clean_text(
                match.group(2)
            )

            if (
                normalize(subject)
                == concept_normalized
                and predicate
            ):
                pass

        # -----------------------------------------------------
        # Includes / consists of / comprises
        # -----------------------------------------------------

        match = re.search(
            r"\b(?:includes|include|consists of|comprises)\s+"
            r"(.+?)[.!?]?$",
            evidence_text,
            re.I
        )

        if match and concept_normalized in normalize(
            evidence_text[:match.start()]
        ):
            components = clean_text(
                match.group(1)
            )

            add(
                f"Which set of elements is included in {concept}?",
                components,
                [
                    "linear, quadratic and exponential laws",
                    "reflexive, symmetric and transitive laws",
                    "Newton's, Ohm's and Kirchhoff's laws",
                ],
                "components",
            )


        # -----------------------------------------------------
        # Used for / used to
        # -----------------------------------------------------

        match = re.search(
            r"\b(?:used to|used for|helps to|serves to|"
            r"designed to)\s+(.+?)[.!?]?$",
            evidence_text,
            re.I
        )

        if match and concept_normalized in normalize(
            evidence_text[:match.start()]
        ):
            purpose = clean_text(
                match.group(1)
            )

            subject_form = concept

            if normalize(concept).endswith("functions"):
                application_question = (
                    f"What are {subject_form} used to do?"
                )
            else:
                application_question = (
                    f"What is {subject_form} used to do?"
                )

            add(
                application_question,
                purpose,
                [
                    "measure physical temperature",
                    "store unrelated numerical data",
                    "replace all mathematical operations",
                ],
                "application",
            )

            add(
                f"Which application is directly supported for {concept}?",
                purpose,
                [
                    "measuring physical temperature",
                    "storing unrelated numerical data",
                    "replacing mathematical operations",
                ],
                "application",
            )

    return candidates


def generate_questions(
    text,
    number=10,
    analysis=None,
):
    """
    PaperScope Question Intelligence Engine v17.

    Evidence-first generation.

    The generator does NOT depend on one question per concept.
    It extracts multiple educational relationships from the source:

      - definitions
      - representations
      - components
      - operations
      - purposes
      - relationships
      - applications

    Questions are then validated and diversified.
    """

    sentences = split_sentences(text)

    if not sentences:
        return []

    # ---------------------------------------------------------
    # Build concept analysis when available.
    # ---------------------------------------------------------

    concept_analysis = []

    if analysis:
        concept_analysis = (
            analysis.get("concept_analysis", {})
            .get("concepts", [])
        )

    if not concept_analysis:
        generated = build_concept_analysis(text)
        concept_analysis = generated.get("concepts", [])

    # ---------------------------------------------------------
    # Evidence-first candidate generation.
    # ---------------------------------------------------------

    candidates = []

    def clean(value):
        return re.sub(
            r"\s+",
            " ",
            str(value).strip(" .,:;")
        )

    def add_candidate(
        question,
        correct,
        distractors,
        question_type,
        evidence,
        difficulty="medium",
        concept="",
    ):
        question = clean(question)
        correct = clean(correct)

        if not question or not correct:
            return

        distractors_clean = []

        for item in distractors:
            item = clean(item)

            if not item:
                continue

            if normalize(item) == normalize(correct):
                continue

            if normalize(item) in {
                normalize(x)
                for x in distractors_clean
            }:
                continue

            distractors_clean.append(item)

        if len(distractors_clean) < 3:
            return

        options = [
            correct,
            *distractors_clean[:3]
        ]

        # Make sure all four options are genuinely different.
        normalized_options = [
            normalize(x)
            for x in options
        ]

        if len(set(normalized_options)) != 4:
            return

        # Stable deterministic shuffle.
        rng = random.Random(
            7919 * (len(candidates) + 1)
        )
        rng.shuffle(options)

        candidates.append({
            "question": question,
            "correct": correct,
            "options": options,
            "answer": options.index(correct),
            "question_type": question_type,
            "difficulty": difficulty,
            "concept": concept or "General Concepts",
            "topic": "General Concepts",
            "explanation": (
                "The answer is directly supported by "
                "the source evidence."
            ),
            "source_sentence": [
                {
                    "sentence": evidence,
                    "score": 1.0,
                }
            ],
        })

    # ---------------------------------------------------------
    # Candidate concept pool.
    # ---------------------------------------------------------

    pool = []

    for item in concept_analysis:
        if isinstance(item, dict):
            value = item.get("concept", "")
        else:
            value = str(item)

        value = clean(value)

        if value:
            pool.append(value)

    # Remove duplicates.
    pool = list(dict.fromkeys(pool))

    # ---------------------------------------------------------
    # Helper: related concept distractors.
    # ---------------------------------------------------------

    def related_distractors(correct):
        values = []

        for item in pool:
            if normalize(item) == normalize(correct):
                continue

            if normalize(item) in normalize(correct):
                continue

            if normalize(correct) in normalize(item):
                continue

            values.append(item)

        return values

    # ---------------------------------------------------------
    # Analyze EVERY source sentence.
    # ---------------------------------------------------------

    for sentence in sentences:

        evidence = clean(sentence)

        if not evidence:
            continue

        lowered = evidence.lower()

        # -----------------------------------------------------
        # 1. DEFINITION
        # -----------------------------------------------------

        match = re.search(
            r"^(.+?)\s+(?:is|are|refers to|means|is defined as)\s+(.+?)\.?$",
            evidence,
            re.I
        )

        if match:

            subject = clean(match.group(1))
            definition = clean(match.group(2))

            if len(subject.split()) <= 6:

                distractors = related_distractors(
                    subject
                )

                add_candidate(
                    (
                        f"Which statement best defines "
                        f"{subject}?"
                    ),
                    definition,
                    distractors,
                    "definition",
                    evidence,
                    "medium",
                    subject,
                )

        # -----------------------------------------------------
        # 2. REPRESENTATION
        # -----------------------------------------------------

        match = re.search(
            r"^(.+?)\s+can be represented using\s+(.+?)\.?$",
            evidence,
            re.I
        )

        if match:

            subject = clean(match.group(1))
            representation = clean(match.group(2))

            distractors = [
                item
                for item in [
                    "flowchart",
                    "database table",
                    "graph",
                    "sequence diagram",
                    "mathematical equation",
                ]
                if normalize(item)
                != normalize(representation)
            ]

            add_candidate(
                f"How can {subject.lstrip('aA ')} be represented?",
                representation,
                distractors,
                "representation",
                evidence,
                "medium",
                subject,
            )

        # -----------------------------------------------------
        # 3. BASIC OPERATIONS / COMPONENTS
        # -----------------------------------------------------

        match = re.search(
            r"^(.+?)\s+(?:are|is)\s+basic\s+(.+?)\.?$",
            evidence,
            re.I
        )

        if match:

            items = clean(match.group(1))
            category = clean(match.group(2))

            parts = [
                x.strip()
                for x in re.split(
                    r",|\band\b",
                    items,
                    flags=re.I
                )
                if x.strip()
            ]

            if len(parts) >= 2:

                alternatives = [
                    "XOR, XNOR and NAND",
                    "ADD, SUBTRACT and MULTIPLY",
                    "READ, WRITE and EXECUTE",
                    "INPUT, OUTPUT and STORAGE",
                ]

                add_candidate(
                    (
                        f"Which set represents the basic "
                        f"{category}?"
                    ),
                    items,
                    alternatives,
                    "components",
                    evidence,
                    "medium",
                    category,
                )

        # -----------------------------------------------------
        # 4. INCLUDES / CONSISTS OF / COMPRISES
        # -----------------------------------------------------

        match = re.search(
            r"^(.+?)\s+(?:includes|consists of|comprises)\s+(.+?)\.?$",
            evidence,
            re.I
        )

        if match:

            subject = clean(match.group(1))
            components = clean(match.group(2))

            distractors = [
                item
                for item in [
                    "linear, quadratic and exponential laws",
                    "reflexive, symmetric and transitive laws",
                    "Newton's, Ohm's and Kirchhoff's laws",
                    "random numerical rules",
                ]
                if normalize(item)
                != normalize(components)
            ]

            add_candidate(
                (
                    f"Which set of elements is included "
                    f"in {subject}?"
                ),
                components,
                distractors,
                "components",
                evidence,
                "easy",
                subject,
            )

        # -----------------------------------------------------
        # 5. PURPOSE / APPLICATION
        # -----------------------------------------------------

        match = re.search(
            r"^(.+?)\s+(?:are|is)\s+used\s+to\s+(.+?)\.?$",
            evidence,
            re.I
        )

        if match:

            subject = clean(match.group(1))
            purpose = clean(match.group(2))

            distractors = [
                "store unrelated numerical data",
                "measure physical temperature",
                "replace all statistical methods",
                "perform chemical reactions",
            ]

            add_candidate(
                f"What are {subject} used to do?",
                purpose,
                distractors,
                "application",
                evidence,
                "medium",
                subject,
            )

        # -----------------------------------------------------
        # 6. COMBINES / USES
        # -----------------------------------------------------

        match = re.search(
            r"^(.+?)\s+(?:combine|combines)\s+(.+?)\s+"
            r"using\s+(.+?)\.?$",
            evidence,
            re.I
        )

        if match:

            subject = clean(match.group(1))
            target = clean(match.group(2))
            mechanism = clean(match.group(3))

            add_candidate(
                (
                    f"Which elements do {subject} combine "
                    f"using {mechanism}?"
                ),
                target,
                related_distractors(target),
                "relationship",
                evidence,
                "medium",
                subject,
            )

    # ---------------------------------------------------------
    # Additional concept-supported questions.
    #
    # These are generated only from actual source evidence.
    # ---------------------------------------------------------

    for item in concept_analysis:

        if len(candidates) >= number * 3:
            break

        if not isinstance(item, dict):
            continue

        concept = clean(
            item.get("concept", "")
        )

        evidence_list = item.get(
            "evidence",
            []
        )

        if not concept or not evidence_list:
            continue

        evidence = evidence_list[0]

        if isinstance(evidence, dict):
            evidence = evidence.get(
                "sentence",
                ""
            )

        evidence = clean(evidence)

        if not evidence:
            continue

        # Avoid generic "identify the concept" questions.
        if concept.lower() in evidence.lower():

            related = related_distractors(
                concept
            )

            if len(related) >= 3:

                add_candidate(
                    (
                        f"Which statement is most closely "
                        f"associated with {concept}?"
                    ),
                    evidence,
                    related,
                    "understanding",
                    evidence,
                    "medium",
                    concept,
                )

    # ---------------------------------------------------------
    # Candidate quality scoring
    # ---------------------------------------------------------
    #
    # Prefer:
    #   1. direct evidence
    #   2. specific educational relationships
    #   3. diverse question types
    #   4. concise questions
    #
    # Avoid:
    #   - near-identical wording
    #   - generic association questions
    #   - repeated application questions
    # ---------------------------------------------------------

    def candidate_quality(candidate):

        question = normalize(
            candidate.get("question", "")
        )

        answer = normalize(
            candidate.get("correct", "")
        )

        question_type = candidate.get(
            "question_type",
            ""
        )

        score = 0.0

        # Evidence-backed educational relationships.
        type_scores = {
            "relationship": 5.0,
            "representation": 5.0,
            "components": 5.0,
            "definition": 5.0,
            "application": 4.5,
            "understanding": 4.0,
            "identification": 3.0,
            "association": 1.0,
        }

        score += type_scores.get(
            question_type,
            2.0
        )

        # Prefer answers containing meaningful information.
        if len(answer.split()) >= 2:
            score += 1.0

        # Penalize overly generic wording.
        generic_terms = {
            "associated with",
            "related to",
            "directly supported",
            "correctly identifies",
        }

        for term in generic_terms:
            if term in question:
                score -= 2.0

        # Penalize very short questions.
        if len(question.split()) < 5:
            score -= 1.0

        # Prefer concise questions over long awkward ones.
        if len(question.split()) <= 12:
            score += 0.5

        candidate["_quality_score"] = score

        return score

    for candidate in candidates:
        candidate_quality(candidate)

    # Sort strongest candidates first.
    candidates.sort(
        key=lambda item: item.get(
            "_quality_score",
            0.0
        ),
        reverse=True,
    )


    # ---------------------------------------------------------
    # Deduplicate candidates.
    # ---------------------------------------------------------

    unique_candidates = []
    seen_questions = set()

    for candidate in candidates:

        key = normalize(
            candidate["question"]
        )

        if not key:
            continue

        if key in seen_questions:
            continue

        seen_questions.add(key)
        unique_candidates.append(candidate)

    # ---------------------------------------------------------
    # Diversification + semantic deduplication.
    # ---------------------------------------------------------

    questions = []

    used_question_types = Counter()
    used_concepts = set()
    used_answer_keys = set()

    def question_signature(candidate):
        """
        Build a stable semantic signature for a generated question.
        """

        qtype = candidate.get(
            "question_type",
            ""
        )

        concept = normalize(
            candidate.get(
                "concept",
                ""
            )
        )

        # Evidence candidates contain "correct".
        # Final MCQ objects get "options"/"answer" later.
        answer = normalize(
            candidate.get(
                "correct",
                ""
            )
        )

        return (
            qtype,
            concept,
            answer,
        )

    used_signatures = set()

    # ---------------------------------------------------------
    # Pass 1:
    # Prefer different concepts, question types and answers.
    # ---------------------------------------------------------

    for candidate in unique_candidates:

        if len(questions) >= number:
            break

        signature = question_signature(
            candidate
        )

        if signature in used_signatures:
            continue

        qtype = candidate.get(
            "question_type",
            ""
        )

        concept = normalize(
            candidate.get(
                "concept",
                ""
            )
        )

        # Evidence candidates use "correct" as their
        # answer field. Final options are created later.
        correct_answer = candidate.get(
            "correct",
            ""
        )

        if not correct_answer:
            continue

        answer_key = normalize(
            correct_answer
        )

        # Don't repeatedly test the exact same answer
        # through different wording.
        if answer_key in used_answer_keys:
            continue

        # No more than two questions of the same family
        # unless the material has no other valid families.
        if used_question_types[qtype] >= 2:
            continue

        questions.append(candidate)

        used_signatures.add(signature)
        used_question_types[qtype] += 1
        used_concepts.add(concept)
        used_answer_keys.add(answer_key)

    # ---------------------------------------------------------
    # Pass 2:
    # Fill remaining slots with unseen semantic signatures.
    # ---------------------------------------------------------

    if len(questions) < number:

        for candidate in unique_candidates:

            if len(questions) >= number:
                break

            if candidate in questions:
                continue

            signature = question_signature(
                candidate
            )

            if signature in used_signatures:
                continue

            questions.append(candidate)
            used_signatures.add(signature)

    # ---------------------------------------------------------
    # Pass 3:
    # Only if necessary, permit repeated answers but NEVER
    # repeated question signatures.
    # ---------------------------------------------------------

    if len(questions) < number:

        for candidate in unique_candidates:

            if len(questions) >= number:
                break

            signature = question_signature(
                candidate
            )

            if signature in used_signatures:
                continue

            questions.append(candidate)
            used_signatures.add(signature)

    # ---------------------------------------------------------
    # Final IDs and topics.
    # ---------------------------------------------------------

    for index, question in enumerate(
        questions[:number],
        1
    ):

        question["id"] = (
            f"PS-Q{index:04d}"
        )

        # Try to inherit topic from concept analysis.
        concept_key = normalize(
            question.get("concept", "")
        )

        for item in concept_analysis:

            if not isinstance(item, dict):
                continue

            if normalize(
                item.get("concept", "")
            ) == concept_key:

                question["topic"] = item.get(
                    "topic",
                    "General Concepts"
                )

                break

    return questions[:number]

def generate_questions_from_analysis(
    text,
    analysis=None,
    number=10,
):

    return generate_questions(
        text=text,
        number=number,
        analysis=analysis,
    )


# Compatibility with existing imports.
QuestionIntelligenceEngine = type(
    "QuestionIntelligenceEngine",
    (),
    {
        "generate_questions": staticmethod(
            generate_questions
        ),
        "generate_questions_from_analysis":
            staticmethod(
                generate_questions_from_analysis
            ),
    }
)
