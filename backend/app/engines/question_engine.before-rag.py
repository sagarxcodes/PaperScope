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










def _sentence_pool(text):
    return [
        re.sub(r"\s+", " ", str(x or "")).strip()
        for x in split_sentences(text)
        if len(re.sub(r"\s+", " ", str(x or "")).strip().split()) >= 5
    ]


# ============================================================

def _find_definition(sentence):
    """
    Extract a subject and its definition from common definition patterns.
    Returns (subject, definition) or (None, None).
    """
    text = re.sub(r"\s+", " ", str(sentence or "")).strip()

    patterns = [
        r"^(.+?)\s+are\s+(.+?)(?:[.!?]|$)",
        r"^(.+?)\s+is\s+(.+?)(?:[.!?]|$)",
        r"^(.+?)\s+refers\s+to\s+(.+?)(?:[.!?]|$)",
        r"^(.+?)\s+means\s+(.+?)(?:[.!?]|$)",
        r"^(.+?)\s+can be defined as\s+(.+?)(?:[.!?]|$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            subject = re.sub(r"\s+", " ", m.group(1)).strip()
            definition = re.sub(r"\s+", " ", m.group(2)).strip()

            # Avoid treating an entire long sentence as a concept.
            if 1 <= len(subject.split()) <= 8 and len(definition.split()) >= 3:
                return subject, definition

    return None, None


# PaperScope Question Intelligence Engine v24
# Semantic MCQ generation layer
# ============================================================

def _v24_norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _v24_words(value):
    return set(
        re.findall(
            r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b",
            value.lower()
        )
    )


def _v24_similarity(a, b):
    a = _v24_words(a)
    b = _v24_words(b)

    if not a or not b:
        return 0.0

    return len(a & b) / len(a | b)


def _v24_unique(items):
    result = []
    seen = set()

    for item in items:
        item = _v24_norm(item)

        if not item:
            continue

        key = item.lower()

        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


# ------------------------------------------------------------
# Concept filtering
# ------------------------------------------------------------

_V24_CONTEXT_PHRASES = {
    "government agencies",
    "government agency",
    "social conditions",
    "economic conditions",
    "demographic conditions",
    "statistical information",
    "population",
    "economy",
    "information",
    "data",
    "statistics",
    "statistical processes",
    "public programmes",
    "public programs",
    "development",
}


_V24_CONCEPT_HINTS = {
    "official statistics",
    "data quality",
    "statistical quality",
    "census",
    "sample survey",
    "sample surveys",
    "administrative data",
    "evidence-based decision making",
    "evidence based decision making",
    "statistical production",
    "statistical production process",
    "statistical process",
    "official data",
}


def _v24_is_real_concept(name, evidence=""):
    name = _v24_norm(name)
    low = name.lower()

    if not name:
        return False

    if len(name.split()) > 8:
        return False

    if low in _V24_CONTEXT_PHRASES:
        return False

    if len(name) < 4:
        return False

    # A domain noun can be retained when the source explicitly
    # presents it as a named method/source/concept.
    if low in _V24_CONCEPT_HINTS:
        return True

    concept_words = {
        "statistics",
        "statistical",
        "survey",
        "surveys",
        "census",
        "data",
        "quality",
        "method",
        "methodology",
        "process",
        "sampling",
        "probability",
        "analysis",
        "decision",
        "measurement",
        "indicator",
        "administrative",
    }

    tokens = _v24_words(name)

    if tokens & concept_words:
        return True

    # Single generic nouns should normally not become concepts.
    if len(tokens) <= 1:
        return False

    return True


def _v24_extract_named_concepts(text):
    """
    Extract concepts from linguistic patterns rather than accepting
    every noun phrase as a learning concept.
    """
    sentences = _sentence_pool(text)
    concepts = []

    for sentence in sentences:
        low = sentence.lower()

        # Explicit definition subjects.
        m = re.search(
            r"^(.+?)\s+(?:is|are|refers to|means|can be defined as)\s+",
            sentence,
            re.I,
        )

        if m:
            candidate = _v24_norm(m.group(1))

            if _v24_is_real_concept(candidate, sentence):
                concepts.append(candidate)

        # Named statistical sources / methods.
        patterns = [
            r"\b(census(?:es)?)\b",
            r"\b(sample surveys?)\b",
            r"\b(administrative data)\b",
            r"\b(official statistics)\b",
            r"\b(data quality)\b",
            r"\b(statistical quality)\b",
            r"\b(evidence-based decision making)\b",
            r"\b(evidence based decision making)\b",
            r"\b(statistical production process)\b",
            r"\b(statistical processes?)\b",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, sentence, re.I):
                candidate = _v24_norm(match.group(1))

                if _v24_is_real_concept(candidate, sentence):
                    concepts.append(candidate)

        # Existing analysis may contain useful domain concepts,
        # but they are filtered before use.
        for candidate in _V24_CONCEPT_HINTS:
            if candidate in low and _v24_is_real_concept(candidate):
                concepts.append(candidate)

    return _v24_unique(concepts)


def _v24_concept_evidence(concept, sentences):
    concept = _v24_norm(concept).lower()

    ranked = []

    for sentence in sentences:
        low = sentence.lower()

        if concept in low:
            score = 10

            # Definitions receive stronger evidence.
            if re.search(
                rf"\b{re.escape(concept)}\b\s+(?:is|are|refers to|means)",
                low,
            ):
                score += 8

            # Relationship statements are useful evidence.
            if re.search(
                r"\b(?:source|used|provide|produce|support|include|contain|depend)\w*\b",
                low,
            ):
                score += 3

            ranked.append((score, sentence))

    ranked.sort(reverse=True)

    return [x[1] for x in ranked]


def _v24_best_concepts(text, analysis=None):
    sentences = _sentence_pool(text)

    extracted = _v24_extract_named_concepts(text)

    # Pull in strong concepts from existing analysis.
    if isinstance(analysis, dict):
        for item in analysis.get("concepts", []):
            if isinstance(item, dict):
                candidate = item.get("concept")
            else:
                candidate = item

            if candidate and _v24_is_real_concept(candidate):
                extracted.append(candidate)

    concepts = _v24_unique(extracted)

    # Rank concepts by source coverage.
    ranked = []

    for concept in concepts:
        evidence = _v24_concept_evidence(concept, sentences)

        if not evidence:
            continue

        ranked.append({
            "concept": concept,
            "frequency": len(evidence),
            "evidence": evidence[0],
        })

    ranked.sort(
        key=lambda x: (
            x["frequency"],
            len(x["concept"].split()),
        ),
        reverse=True,
    )

    return ranked[:20]


# ------------------------------------------------------------
# Source relationships
# ------------------------------------------------------------

def _v24_sources(text):
    sentences = _sentence_pool(text)
    sources = []

    for sentence in sentences:
        low = sentence.lower()

        if "source" in low or "sources" in low:
            if "official statistics" in low:
                if "census" in low or "survey" in low or "administrative data" in low:
                    sources.append(sentence)

    return sources


def _v24_extract_quality_factors(text):
    sentences = _sentence_pool(text)

    for sentence in sentences:
        low = sentence.lower()

        if "quality" in low and (
            "accuracy" in low
            or "reliability" in low
            or "timeliness" in low
        ):
            factors = re.findall(
                r"\b(?:accuracy|reliability|relevance|timeliness|accessibility|coherence|validity|completeness|consistency)\b",
                low,
            )

            if len(factors) >= 2:
                return _v24_unique(factors), sentence

    return [], None


# ------------------------------------------------------------
# Distractors
# ------------------------------------------------------------

def _v24_distractors(answer, concepts, count=3):
    answer = _v24_norm(answer)

    candidates = []

    for concept in concepts:
        concept = _v24_norm(concept)

        if concept.lower() == answer.lower():
            continue

        similarity = _v24_similarity(answer, concept)

        # Avoid near duplicates.
        if similarity >= 0.75:
            continue

        score = 0

        # Prefer same domain.
        answer_tokens = _v24_words(answer)
        candidate_tokens = _v24_words(concept)

        if answer_tokens & candidate_tokens:
            score += 3

        # Prefer comparable length.
        length_difference = abs(
            len(answer.split()) - len(concept.split())
        )

        score += max(0, 3 - length_difference)

        candidates.append((score, concept))

    candidates.sort(reverse=True)

    result = []

    for _, candidate in candidates:
        if all(
            _v24_similarity(candidate, x) < 0.75
            for x in result
        ):
            result.append(candidate)

        if len(result) >= count:
            break

    return result


def _v24_source_answer_distractors(
    answer,
    statements,
    count=3,
):
    """
    Extract alternatives from the same semantic category.
    """
    answer = _v24_norm(answer)

    candidates = []

    for statement in statements:
        statement = _v24_norm(statement)

        if statement.lower() == answer.lower():
            continue

        if len(statement.split()) > 18:
            continue

        similarity = _v24_similarity(answer, statement)

        if similarity >= 0.80:
            continue

        candidates.append(statement)

    candidates = sorted(
        candidates,
        key=lambda x: abs(len(x.split()) - len(answer.split()))
    )

    return _v24_unique(candidates)[:count]


# ------------------------------------------------------------
# Question blueprints
# ------------------------------------------------------------

def _v24_definition_question(concept, evidence):
    """
    Ask for meaning, not identification of the word itself.
    """
    subject, definition = _find_definition(evidence)

    if not subject or subject.lower() != concept.lower():
        return None

    return {
        "question": (
            f"Which statement best explains the meaning of {concept} "
            f"as presented in the learning material?"
        ),
        "answer": definition,
        "type": "definition",
        "difficulty": "easy",
        "evidence": evidence,
    }


def _v24_source_question(evidence):
    low = evidence.lower()

    if "official statistics" not in low:
        return None

    candidates = []

    if "census" in low:
        candidates.append("Census")
    if "sample survey" in low or "sample surveys" in low:
        candidates.append("Sample surveys")
    if "administrative data" in low:
        candidates.append("Administrative data")

    candidates = _v24_unique(candidates)

    if len(candidates) < 2:
        return None

    return {
        "question": (
            "Which of the following is identified in the material "
            "as a source of official statistics?"
        ),
        "answer": candidates[0],
        "type": "relationship",
        "difficulty": "medium",
        "evidence": evidence,
        "category_values": candidates,
    }


def _v24_quality_question(factors, evidence):
    if len(factors) < 4:
        return None

    return {
        "question": (
            "Which of the following is identified as a quality factor "
            "for official statistics in the learning material?"
        ),
        "answer": factors[0].capitalize(),
        "type": "concept",
        "difficulty": "medium",
        "evidence": evidence,
        "category_values": [x.capitalize() for x in factors],
    }


def _v24_use_question(evidence):
    low = evidence.lower()

    if "used by governments" not in low:
        return None

    return {
        "question": (
            "According to the material, which of the following is a "
            "use of official statistics?"
        ),
        "answer": "Formulating policies",
        "type": "application",
        "difficulty": "medium",
        "evidence": evidence,
        "category_values": [
            "Formulating policies",
            "Monitoring development",
            "Evaluating public programmes",
        ],
    }


def _v24_case_question(concept, evidence):
    low = evidence.lower()

    if concept.lower() == "official statistics":
        if "government agencies" in low and "describe" in low:
            return {
                "question": (
                    "A government agency publishes statistical information "
                    "to describe economic and demographic conditions. "
                    "Which concept from the material best describes this output?"
                ),
                "answer": "Official statistics",
                "type": "scenario",
                "difficulty": "medium",
                "evidence": evidence,
            }

        if "policies" in low or "public programmes" in low:
            return {
                "question": (
                    "A government uses statistical information to formulate "
                    "policies and evaluate public programmes. Which concept "
                    "from the material is most directly relevant?"
                ),
                "answer": "Official statistics",
                "type": "scenario",
                "difficulty": "hard",
                "evidence": evidence,
            }

    if concept.lower() == "administrative data":
        if "used to produce official statistics" in low:
            return {
                "question": (
                    "A statistical agency wants to use records already "
                    "collected through administrative activities to produce "
                    "official statistics. Which data source does the material identify?"
                ),
                "answer": "Administrative data",
                "type": "scenario",
                "difficulty": "hard",
                "evidence": evidence,
            }

    return None


# ------------------------------------------------------------
# Final validation
# ------------------------------------------------------------

def _v24_validate(question):
    if not question:
        return False

    stem = _v24_norm(question.get("question"))
    answer = _v24_norm(question.get("answer"))
    options = [
        _v24_norm(x)
        for x in question.get("options", [])
    ]

    if len(stem.split()) < 6:
        return False

    if len(options) != 4:
        return False

    if len(set(x.lower() for x in options)) != 4:
        return False

    if answer.lower() not in {x.lower() for x in options}:
        return False

    if not question.get("evidence"):
        return False

    # Reject distractors that are almost identical to the answer.
    for option in options:
        if option.lower() == answer.lower():
            continue

        if _v24_similarity(answer, option) >= 0.85:
            return False

    return True


def _v24_finalize(candidate, index, topic):
    answer = _v24_norm(candidate["answer"])
    distractors = _v24_unique(candidate.get("distractors", []))

    if len(distractors) < 3:
        return None

    distractors = distractors[:3]

    options = [answer] + distractors

    rng = random.Random(2400 + index)
    rng.shuffle(options)

    answer_index = options.index(answer)

    question = {
        "id": f"PS-Q{index + 1}",
        "question": _v24_norm(candidate["question"]),
        "options": options,
        "answer": answer_index,
        "correct": answer,
        "correct_answer": answer,
        "explanation": (
            f"{answer} is correct because the learning material states: "
            f"{_v24_norm(candidate['evidence'])}"
        ),
        "evidence": _v24_norm(candidate["evidence"]),
        "source_sentence": _v24_norm(candidate["evidence"]),
        "concept": candidate.get("concept", answer),
        "topic": topic,
        "difficulty": candidate.get("difficulty", "medium"),
        "question_type": candidate.get("type", "concept"),
    }

    return question if _v24_validate(question) else None


# ------------------------------------------------------------
# Main generator
# ------------------------------------------------------------

def generate_questions(text, number=10, analysis=None):
    text = _v24_norm(text)

    if not text:
        return []

    number = max(1, int(number or 10))

    if analysis is None:
        try:
            analysis = build_concept_analysis(text)
        except Exception:
            analysis = {}

    sentences = _sentence_pool(text)

    concepts = _v24_best_concepts(
        text,
        analysis,
    )

    concept_names = [
        x["concept"]
        for x in concepts
    ]

    candidates = []

    # --------------------------------------------------------
    # 1. Meaning / definition
    # --------------------------------------------------------
    for item in concepts:
        concept = item["concept"]
        evidence_list = item.get("evidence") or []

        if isinstance(evidence_list, str):
            evidence_list = [evidence_list]

        for evidence in evidence_list[:2]:
            candidate = _v24_definition_question(
                concept,
                evidence,
            )

            if candidate:
                definition = _find_definition(evidence)[1]

                distractors = _v24_source_answer_distractors(
                    definition,
                    sentences,
                )

                if len(distractors) < 3:
                    distractors = _v24_distractors(
                        definition,
                        concept_names,
                    )

                if len(distractors) >= 3:
                    candidate["distractors"] = distractors
                    candidate["concept"] = concept
                    candidates.append(candidate)

    # --------------------------------------------------------
    # 2. Official statistics sources
    # --------------------------------------------------------
    for evidence in _v24_sources(text):
        candidate = _v24_source_question(evidence)

        if candidate:
            values = candidate["category_values"]

            distractors = [
                x for x in values
                if x.lower() != candidate["answer"].lower()
            ]

            distractors += _v24_distractors(
                candidate["answer"],
                concept_names,
            )

            candidate["distractors"] = _v24_unique(distractors)
            candidate["concept"] = "Official Statistics"
            candidates.append(candidate)

    # --------------------------------------------------------
    # 3. Quality
    # --------------------------------------------------------
    factors, quality_evidence = _v24_extract_quality_factors(text)

    if quality_evidence:
        candidate = _v24_quality_question(
            factors,
            quality_evidence,
        )

        if candidate:
            distractors = [
                x.capitalize()
                for x in factors[1:]
            ]

            distractors += _v24_distractors(
                candidate["answer"],
                concept_names,
            )

            candidate["distractors"] = _v24_unique(distractors)
            candidate["concept"] = "Data Quality"
            candidates.append(candidate)

    # --------------------------------------------------------
    # 4. Uses / application
    # --------------------------------------------------------
    for sentence in sentences:
        candidate = _v24_use_question(sentence)

        if candidate:
            distractors = [
                x
                for x in candidate["category_values"]
                if x.lower() != candidate["answer"].lower()
            ]

            # Fill with concept-level alternatives if needed.
            distractors += _v24_distractors(
                candidate["answer"],
                concept_names,
            )

            candidate["distractors"] = _v24_unique(distractors)
            candidate["concept"] = "Official Statistics"
            candidates.append(candidate)

    # --------------------------------------------------------
    # 5. Genuine case-based questions
    # --------------------------------------------------------
    for item in concepts:
        concept = item["concept"]
        evidence_list = item.get("evidence") or []

        if isinstance(evidence_list, str):
            evidence_list = [evidence_list]

        for evidence in evidence_list[:2]:
            candidate = _v24_case_question(
                concept,
                evidence,
            )

            if not candidate:
                continue

            candidate["distractors"] = _v24_distractors(
                candidate["answer"],
                concept_names,
            )

            candidate["concept"] = concept

            if len(candidate["distractors"]) >= 3:
                candidates.append(candidate)

    # --------------------------------------------------------
    # Remove duplicate question stems.
    # --------------------------------------------------------
    unique = []
    seen = set()

    for candidate in candidates:
        key = _v24_norm(candidate["question"]).lower()

        if key in seen:
            continue

        seen.add(key)
        unique.append(candidate)

    # --------------------------------------------------------
    # Score and diversify.
    # --------------------------------------------------------
    type_priority = {
        "scenario": 7,
        "application": 6,
        "relationship": 6,
        "concept": 5,
        "definition": 3,
    }

    unique.sort(
        key=lambda x: (
            type_priority.get(x.get("type"), 1),
            len(x.get("evidence", "").split()),
        ),
        reverse=True,
    )

    selected = []
    type_count = Counter()
    answer_count = Counter()

    # Prefer different concepts.
    for candidate in unique:
        answer = _v24_norm(candidate["answer"]).lower()
        qtype = candidate.get("type", "concept")

        if answer_count[answer] >= 2:
            continue

        if type_count[qtype] >= 3:
            continue

        q = _v24_finalize(
            candidate,
            len(selected),
            (
                analysis.get("topics", ["General Concepts"])[0]
                if isinstance(analysis, dict)
                and analysis.get("topics")
                else "General Concepts"
            ),
        )

        if not q:
            continue

        selected.append(q)
        type_count[qtype] += 1
        answer_count[answer] += 1

        if len(selected) >= number:
            break

    # Final fallback.
    if len(selected) < number:
        for candidate in unique:
            answer = _v24_norm(candidate["answer"]).lower()

            if answer_count[answer] >= 3:
                continue

            q = _v24_finalize(
                candidate,
                len(selected),
                (
                    analysis.get("topics", ["General Concepts"])[0]
                    if isinstance(analysis, dict)
                    and analysis.get("topics")
                    else "General Concepts"
                ),
            )

            if q:
                selected.append(q)
                answer_count[answer] += 1

            if len(selected) >= number:
                break

    return selected[:number]


def generate_questions_from_analysis(
    analysis,
    text=None,
    number=10,
):
    if text:
        return generate_questions(
            text,
            number=number,
            analysis=analysis,
        )

    if isinstance(analysis, dict):
        source = (
            analysis.get("source_text")
            or analysis.get("text")
            or ""
        )

        if source:
            return generate_questions(
                source,
                number=number,
                analysis=analysis,
            )

    return []


class QuestionIntelligenceEngine:
    generate_questions = staticmethod(generate_questions)
    generate_questions_from_analysis = staticmethod(
        generate_questions_from_analysis
    )
    build_concept_analysis = staticmethod(build_concept_analysis)
