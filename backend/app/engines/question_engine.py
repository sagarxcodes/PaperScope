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

def _v24_distractor_key(value):
    """
    Normalize distractors beyond simple lowercase matching.

    This catches variants such as:
    - sample survey
    - sample surveys
    - evidence based
    - evidence-based
    """
    value = _v24_norm(value).lower()
    value = value.replace("-", " ")
    value = re.sub(r"\b(a|an|the)\b", " ", value)
    value = re.sub(r"\b(s)\b", "", value)
    value = re.sub(r"\s+", " ", value).strip()

    # Normalize common plural forms.
    tokens = []
    for token in value.split():
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        tokens.append(token)

    return " ".join(tokens)


def _v24_contains_meaning(container, phrase):
    """
    Detect semantic containment that Jaccard similarity misses.

    Example:
        answer    = 'produced by government agencies'
        candidate = 'Official statistics are produced by government agencies.'

    The candidate should never become a distractor.
    """
    a = _v24_distractor_key(container)
    b = _v24_distractor_key(phrase)

    if not a or not b:
        return False

    return a in b or b in a


def _v24_extract_answer_phrases(answer, statements):
    """
    Extract short phrases from source sentences that can act as
    definition/application alternatives without copying entire sentences.
    """
    answer = _v24_norm(answer)
    answer_key = _v24_distractor_key(answer)

    results = []

    for statement in statements:
        statement = _v24_norm(statement)

        if not statement:
            continue

        # Never use the original answer or a sentence containing it.
        if statement.lower() == answer.lower():
            continue

        if _v24_contains_meaning(statement, answer):
            continue

        # Remove common sentence subjects so the option becomes
        # a comparable predicate/meaning phrase.
        fragments = []

        patterns = [
            r"^[^.?!]+?\s+(?:are|is|were|was)\s+(.+?)[.?!]?$",
            r"^[^.?!]+?\s+(?:include|includes|support|supports|provide|provides|describe|describes|use|uses)\s+(.+?)[.?!]?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                fragments.append(match.group(1))

        # Also consider the complete sentence only if it is already short.
        if len(statement.split()) <= 9:
            fragments.append(statement)

        for fragment in fragments:
            fragment = _v24_norm(fragment).strip(" .,:;")

            if not fragment:
                continue

            if len(fragment.split()) < 2:
                continue

            if len(fragment.split()) > 10:
                continue

            if _v24_distractor_key(fragment) == answer_key:
                continue

            if _v24_contains_meaning(fragment, answer):
                continue

            results.append(fragment)

    return _v24_unique(results)


def _v24_distractor_key(value):
    """
    Normalize distractors beyond simple lowercase matching.

    This catches variants such as:
    - sample survey
    - sample surveys
    - evidence based
    - evidence-based
    """
    value = _v24_norm(value).lower()
    value = value.replace("-", " ")
    value = re.sub(r"\b(a|an|the)\b", " ", value)
    value = re.sub(r"\b(s)\b", "", value)
    value = re.sub(r"\s+", " ", value).strip()

    # Normalize common plural forms.
    tokens = []
    for token in value.split():
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        tokens.append(token)

    return " ".join(tokens)


def _v24_contains_meaning(container, phrase):
    """
    Detect semantic containment that Jaccard similarity misses.

    Example:
        answer    = 'produced by government agencies'
        candidate = 'Official statistics are produced by government agencies.'

    The candidate should never become a distractor.
    """
    a = _v24_distractor_key(container)
    b = _v24_distractor_key(phrase)

    if not a or not b:
        return False

    return a in b or b in a


def _v24_extract_answer_phrases(answer, statements):
    """
    Extract short phrases from source sentences that can act as
    definition/application alternatives without copying entire sentences.
    """
    answer = _v24_norm(answer)
    answer_key = _v24_distractor_key(answer)

    results = []

    for statement in statements:
        statement = _v24_norm(statement)

        if not statement:
            continue

        # Never use the original answer or a sentence containing it.
        if statement.lower() == answer.lower():
            continue

        if _v24_contains_meaning(statement, answer):
            continue

        # Remove common sentence subjects so the option becomes
        # a comparable predicate/meaning phrase.
        fragments = []

        patterns = [
            r"^[^.?!]+?\s+(?:are|is|were|was)\s+(.+?)[.?!]?$",
            r"^[^.?!]+?\s+(?:include|includes|support|supports|provide|provides|describe|describes|use|uses)\s+(.+?)[.?!]?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                fragments.append(match.group(1))

        # Also consider the complete sentence only if it is already short.
        if len(statement.split()) <= 9:
            fragments.append(statement)

        for fragment in fragments:
            fragment = _v24_norm(fragment).strip(" .,:;")

            if not fragment:
                continue

            if len(fragment.split()) < 2:
                continue

            if len(fragment.split()) > 10:
                continue

            if _v24_distractor_key(fragment) == answer_key:
                continue

            if _v24_contains_meaning(fragment, answer):
                continue

            results.append(fragment)

    return _v24_unique(results)


# Domain-aware distractor pools.
# These are ontology-backed/common domain categories, not extracted facts.
_V24_QUALITY_DIMENSIONS = [
    "Accuracy",
    "Reliability",
    "Relevance",
    "Timeliness",
    "Accessibility",
    "Coherence",
    "Completeness",
    "Consistency",
]

_V24_STATISTICAL_SOURCES = [
    "Census",
    "Sample surveys",
    "Administrative data",
    "Vital registration data",
]

_V24_STATISTICS_APPLICATIONS = [
    "Formulating policies",
    "Monitoring development",
    "Evaluating public programmes",
    "Evidence-based decision making",
]


def _v24_distractors(answer, concepts, count=3):
    answer = _v24_norm(answer)

    candidates = []
    answer_key = _v24_distractor_key(answer)

    for concept in concepts:
        concept = _v24_norm(concept)

        if not concept:
            continue

        # Strong normalization catches singular/plural variants.
        if _v24_distractor_key(concept) == answer_key:
            continue

        # Never allow semantic containment.
        if _v24_contains_meaning(answer, concept):
            continue

        similarity = _v24_similarity(answer, concept)

        # Avoid near duplicates.
        if similarity >= 0.75:
            continue

        score = 0

        answer_tokens = _v24_words(answer)
        candidate_tokens = _v24_words(concept)

        if answer_tokens & candidate_tokens:
            score += 3

        length_difference = abs(
            len(answer.split()) - len(concept.split())
        )

        score += max(0, 3 - length_difference)

        # Prefer actual domain concepts over generic context words.
        if concept.lower() in _V24_CONCEPT_HINTS:
            score += 4

        candidates.append((score, concept))

    candidates.sort(
        key=lambda item: (-item[0], item[1].lower())
    )

    result = []

    for _, candidate in candidates:
        if _v24_distractor_key(candidate) == answer_key:
            continue

        if _v24_contains_meaning(answer, candidate):
            continue

        if all(
            _v24_similarity(candidate, x) < 0.75
            and not _v24_contains_meaning(candidate, x)
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

    Importantly, this never returns an entire source sentence that
    already contains the answer.
    """
    answer = _v24_norm(answer)
    answer_key = _v24_distractor_key(answer)

    candidates = []

    for statement in statements:
        statement = _v24_norm(statement)

        if not statement:
            continue

        if _v24_distractor_key(statement) == answer_key:
            continue

        # Critical fix:
        # Do not use a sentence containing the answer as a distractor.
        if _v24_contains_meaning(statement, answer):
            continue

        if len(statement.split()) > 18:
            continue

        similarity = _v24_similarity(answer, statement)

        if similarity >= 0.80:
            continue

        candidates.append(statement)

    # Prefer short comparable phrases.
    candidates = sorted(
        candidates,
        key=lambda x: (
            abs(len(x.split()) - len(answer.split())),
            len(x.split()),
        ),
    )

    return _v24_unique(candidates)[:count]


# ------------------------------------------------------------
# Question blueprints
# ------------------------------------------------------------

def _v24_definition_question(concept, evidence):
    """
    Ask for meaning only when the extracted definition is a
    complete, meaningful answer rather than a weak sentence fragment.
    """
    subject, definition = _find_definition(evidence)

    if not subject or subject.lower() != concept.lower():
        return None

    definition = _v24_norm(definition)

    # Reject weak predicate fragments such as:
    #   "produced by government agencies"
    #   "important sources of official statistics"
    #
    # These are useful evidence internally, but are not strong
    # standalone MCQ answers.
    weak_starts = (
        "produced by ",
        "important ",
        "used for ",
        "used to ",
        "related to ",
        "based on ",
        "available from ",
        "supported by ",
    )

    if definition.lower().startswith(weak_starts):
        return None

    # A definition should contain enough information to stand
    # on its own as an answer option.
    if len(definition.split()) < 5:
        return None

    return {
        "question": (
            f"Which statement best describes {concept} "
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
    """
    Generate a quality-factor MCQ when the material explicitly
    identifies at least two quality dimensions.

    The engine must not invent additional quality dimensions merely
    to satisfy the four-option MCQ format.
    """
    factors = _v24_unique(
        [
            _v24_norm(x).lower()
            for x in (factors or [])
            if _v24_norm(x)
        ]
    )

    if len(factors) < 2 or not evidence:
        return None

    answer = factors[0].capitalize()
    category_values = [
        x.capitalize()
        for x in factors
    ]

    return {
        "question": (
            "Which of the following is identified as a dimension "
            "of statistical data quality in the learning material?"
        ),
        "answer": answer,
        "type": "concept",
        "difficulty": "medium",
        "evidence": evidence,
        "category_values": category_values,
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

    # v24 stores `answer` as the zero-based option index.
    # Older question formats may store the answer text.
    raw_answer = question.get("answer")

    if isinstance(raw_answer, int):
        if raw_answer < 0 or raw_answer >= len(options):
            return False

        answer = options[raw_answer]

    else:
        answer = _v24_norm(raw_answer)

        if answer.lower() not in {x.lower() for x in options}:
            return False

    if not answer:
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

def generate_questions(
    text,
    number=10,
    analysis=None,
    retrieval_context=None,
):
    text = _v24_norm(text)

    # --------------------------------------------------------
    # Retrieval-Augmented Question Generation
    # --------------------------------------------------------
    # Retrieved questions are used as structured evidence about
    # relevant concepts, competencies, question types and
    # difficulty. They are NOT copied into the generated set.
    retrieval_context = retrieval_context or []

    retrieval_concepts = []

    for item in retrieval_context:
        if not isinstance(item, dict):
            continue

        concept = item.get("concept")

        if concept:
            retrieval_concepts.append(
                str(concept).strip()
            )

    retrieval_concepts = list(
        dict.fromkeys(retrieval_concepts)
    )

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

    # Retrieved question-bank concepts provide additional
    # semantic context for distractor selection and coverage.
    for concept in retrieval_concepts:
        if concept and concept not in concept_names:
            concept_names.append(concept)

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
            distractors = [
                x for x in _V24_STATISTICAL_SOURCES
                if x.lower() != candidate["answer"].lower()
            ]

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
                x for x in _V24_QUALITY_DIMENSIONS
                if x.lower() != candidate["answer"].lower()
            ]

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
    # Remove duplicate / near-duplicate question stems.
    # --------------------------------------------------------
    unique = []
    seen = set()

    def _question_stem_key(value):
        value = _v24_norm(value).lower()
        value = re.sub(r"[^a-z0-9\\s]", " ", value)
        value = re.sub(r"\\s+", " ", value).strip()
        return value

    def _is_near_duplicate_stem(value, existing_values):
        key = _question_stem_key(value)

        if not key:
            return True

        if key in existing_values:
            return True

        for existing in existing_values:
            if _v24_similarity(key, existing) >= 0.86:
                return True

        return False

    for candidate in candidates:
        question_text = candidate.get("question", "")

        if _is_near_duplicate_stem(question_text, seen):
            continue

        key = _question_stem_key(question_text)
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

    # --------------------------------------------------------
    # Do not force the requested count.
    #
    # PaperScope should return only questions that survive
    # evidence, structure, distractor, duplication, and
    # diversity checks. A small material may legitimately
    # produce fewer questions than requested.
    # --------------------------------------------------------

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

# ============================================================
# PaperScope Personalized Quiz Intelligence v1
# ============================================================

def _ps_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ps_normalize_concept(value):
    return re.sub(
        r"[^a-z0-9 ]",
        "",
        str(value or "").lower()
    ).strip()


def _ps_mastery_items(learner_profile):
    """
    Accept flexible mastery formats.

    Supported examples:

    {
        "mastery": {
            "Probability": 42,
            "Conditional Probability": 31
        }
    }

    or

    {
        "topic_mastery": [
            {"topic": "Probability", "mastery": 42},
            {"topic": "Statistics", "mastery": 78}
        ]
    }
    """
    profile = learner_profile or {}

    raw = (
        profile.get("mastery")
        or profile.get("topic_mastery")
        or profile.get("competency_mastery")
        or {}
    )

    items = []

    if isinstance(raw, dict):
        for name, score in raw.items():
            items.append({
                "concept": str(name),
                "mastery": _ps_float(score, 0),
            })

    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue

            name = (
                item.get("concept")
                or item.get("topic")
                or item.get("subtopic")
                or item.get("name")
            )

            score = (
                item.get("mastery")
                if item.get("mastery") is not None
                else item.get("accuracy", 0)
            )

            if name:
                items.append({
                    "concept": str(name),
                    "mastery": _ps_float(score, 0),
                })

    return items


def _ps_recent_questions(learner_profile):
    profile = learner_profile or {}

    history = (
        profile.get("recent_questions")
        or profile.get("question_history")
        or profile.get("attempted_questions")
        or []
    )

    result = []

    for item in history:
        if isinstance(item, str):
            result.append(_ps_normalize_concept(item))
        elif isinstance(item, dict):
            question = (
                item.get("question")
                or item.get("text")
                or item.get("stem")
            )

            if question:
                result.append(
                    _ps_normalize_concept(question)
                )

    return result


def _ps_target_concepts(learner_profile, limit=5):
    """
    Weakest competencies receive the highest priority.
    """
    items = _ps_mastery_items(learner_profile)

    items.sort(
        key=lambda item: item["mastery"]
    )

    return [
        item["concept"]
        for item in items[:limit]
    ]


def _ps_question_similarity_to_targets(question, targets):
    """
    Lightweight semantic matching between a generated question
    and the learner's weakest competencies.
    """
    if not targets:
        return 0.0

    question_text = str(
        question.get("question", "")
    ).lower()

    concept = str(
        question.get("concept", "")
    ).lower()

    combined = f"{concept} {question_text}"

    best = 0.0

    for target in targets:
        target = str(target).lower().strip()

        if not target:
            continue

        if target in combined:
            best = max(best, 1.0)
            continue

        target_words = set(
            re.findall(r"[a-zA-Z]{3,}", target)
        )

        question_words = set(
            re.findall(r"[a-zA-Z]{3,}", combined)
        )

        if target_words:
            overlap = len(
                target_words & question_words
            ) / len(target_words)

            best = max(best, overlap)

    return best


def _ps_difficulty_score(question, learner_profile):
    """
    Prefer a difficulty appropriate to the learner.

    The existing generator remains responsible for actually
    determining/validating question difficulty.
    """
    requested = str(
        (learner_profile or {}).get(
            "difficulty",
            "adaptive"
        )
    ).lower()

    difficulty = str(
        question.get("difficulty", "")
    ).lower()

    if requested in {"easy", "medium", "hard"}:
        return 1.0 if requested in difficulty else 0.0

    return 0.5



def generate_personalized_quiz(
    text,
    learner_profile=None,
    number=10,
    analysis=None,
    retrieval_context=None,
):
    """
    PaperScope V26 — Original Question Intelligence.

    The uploaded material is used to identify competencies/concepts.
    Questions themselves are generated from PaperScope's internal
    question-pattern bank and original scenario generators.

    The source material is NOT copied into the question stem.
    """

    learner_profile = learner_profile or {}
    number = max(1, int(number or 10))

    # Get concepts/competencies from the uploaded material.
    concepts = []

    try:
        best = _v24_best_concepts(text, analysis)
    except Exception:
        best = []

    for item in best or []:
        if isinstance(item, dict):
            concept = item.get("concept") or item.get("competency")
            if concept:
                concepts.append(str(concept).strip())
        elif isinstance(item, str):
            concepts.append(item.strip())

    # Include learner's weak competencies.
    try:
        targets = _ps_target_concepts(
            learner_profile,
            limit=max(7, number)
        )
    except Exception:
        targets = []

    for target in targets:
        target = str(target).strip()
        if target and target not in concepts:
            concepts.append(target)

    # If extraction failed, fall back to explicit learner mastery keys.
    if not concepts:
        mastery = learner_profile.get("mastery", {}) or {}
        if isinstance(mastery, dict):
            concepts = [str(k).strip() for k in mastery.keys() if str(k).strip()]

    if not concepts:
        concepts = ["General Statistics"]

    # Generate ORIGINAL scenario-based questions.
    from app.engines.original_question_engine import generate_original_questions

    questions = generate_original_questions(
        concepts=concepts,
        learner_profile=learner_profile,
        number=number,
    )

    # Compatibility + personalization metadata expected by the frontend.
    recent = _ps_recent_questions(learner_profile)

    final = []
    seen = set()

    for q in questions:
        if not isinstance(q, dict):
            continue

        stem = str(q.get("question", "")).strip()
        if not stem:
            continue

        normalized = _ps_normalize_concept(stem)

        if normalized in seen:
            continue

        # Avoid immediately repeating previous questions.
        repeated = False
        for old in recent:
            old_stem = _ps_normalize_concept(
                str(old.get("question", ""))
            )
            if old_stem and (
                old_stem == normalized
                or _v24_similarity(old_stem, normalized) >= 0.88
            ):
                repeated = True
                break

        if repeated:
            continue

        seen.add(normalized)

        competency = (
            q.get("target_competency")
            or q.get("competency")
            or q.get("concept")
            or "General Statistics"
        )

        mastery = _ps_mastery_value(
            learner_profile,
            competency
        )

        q["competency"] = competency
        q["target_competency"] = competency
        q["mastery_before"] = round(float(mastery), 1)

        q["personalization"] = {
            "rank": len(final) + 1,
            "target_competency": competency,
            "current_mastery": round(float(mastery), 1),
            "reason": (
                "Targeted using competency mastery and the "
                "learner's current learning needs."
            ),
        }

        generation = q.setdefault("generation", {})
        generation["engine"] = "PaperScope Original Question Intelligence"
        generation["source_text_used_as_question"] = False
        generation["original_scenario"] = True

        final.append(q)

        if len(final) >= number:
            break

    return final

def _ps_targeted_evidence(text, competency):
    """Find the strongest material evidence specifically related to a competency."""
    competency = str(competency or "").strip()
    if not competency:
        return []

    sentences = _sentence_pool(text)
    target_words = set(_v24_words(competency))

    scored = []
    for sentence in sentences:
        words = set(_v24_words(sentence))
        overlap = len(target_words & words)

        # Also reward partial phrase matches.
        phrase_bonus = 2 if competency.lower() in sentence.lower() else 0

        score = overlap + phrase_bonus
        if score > 0:
            scored.append((score, sentence))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [sentence for _, sentence in scored[:6]]


def _ps_mastery_value(learner_profile, competency):
    mastery = learner_profile.get("mastery", {}) or {}
    target = _ps_normalize_concept(competency)

    for key, value in mastery.items():
        if _ps_normalize_concept(key) == target:
            return _ps_float(value, 50.0)

    return 50.0


def _ps_targeted_difficulty(learner_profile, competency):
    """
    Difficulty is driven by current mastery.
    Low mastery -> easier diagnostic questions.
    Medium mastery -> medium/application.
    High mastery -> harder questions.
    """
    mastery = _ps_mastery_value(learner_profile, competency)

    if mastery < 40:
        return "easy"
    if mastery < 70:
        return "medium"
    return "hard"


def _ps_build_targeted_candidates(text, competency, learner_profile):
    """
    Generate questions specifically from evidence belonging to one weak
    competency. This prevents high-mastery concepts from dominating the quiz.
    """
    evidence_sentences = _ps_targeted_evidence(text, competency)

    if not evidence_sentences:
        return []

    evidence = " ".join(evidence_sentences)
    candidates = []

    concept_names = [
        str(x).strip()
        for x in (_v24_best_concepts(text) or [])
        if isinstance(x, dict) and x.get("concept")
    ]

    if competency not in concept_names:
        concept_names.append(competency)

    # --------------------------------------------------------
    # 1. Definition question
    # --------------------------------------------------------
    try:
        candidate = _v24_definition_question(competency, evidence)

        if candidate:
            answer = candidate.get("answer", "")
            distractors = _v24_distractors(
                answer,
                concept_names,
                count=3
            )

            if len(distractors) >= 3:
                candidate["distractors"] = distractors
                candidate["concept"] = competency
                candidates.append(candidate)
    except Exception:
        pass

    # --------------------------------------------------------
    # 2. Case/application question
    # --------------------------------------------------------
    try:
        candidate = _v24_case_question(competency, evidence)

        if candidate:
            distractors = _v24_distractors(
                candidate.get("answer", ""),
                concept_names,
                count=3
            )

            if len(distractors) >= 3:
                candidate["distractors"] = distractors
                candidate["concept"] = competency
                candidates.append(candidate)
    except Exception:
        pass

    # --------------------------------------------------------
    # 3. Use/application question
    # --------------------------------------------------------
    for sentence in evidence_sentences:
        try:
            candidate = _v24_use_question(sentence)

            if candidate:
                distractors = _v24_distractors(
                    candidate.get("answer", ""),
                    concept_names,
                    count=3
                )

                if len(distractors) >= 3:
                    candidate["distractors"] = distractors
                    candidate["concept"] = competency
                    candidates.append(candidate)
        except Exception:
            pass

    # Validate and remove duplicates.
    valid = []
    seen = set()

    for candidate in candidates:
        try:
            if not _v24_validate(candidate):
                continue
        except Exception:
            continue

        key = _ps_normalize_concept(candidate.get("question", ""))

        if key in seen:
            continue

        seen.add(key)
        valid.append(candidate)

    return valid


def _legacy_generate_personalized_quiz_v25(
    text,
    learner_profile=None,
    number=10,
    analysis=None,
    retrieval_context=None,
):
    """
    PaperScope personalized quiz engine.

    Priority:
      1. Lowest-mastery competencies
      2. Evidence specifically about those competencies
      3. Targeted question generation
      4. Adaptive difficulty
      5. Recent-question avoidance
      6. Generic fallback only when targeted evidence is insufficient
    """

    learner_profile = learner_profile or {}
    number = max(1, int(number or 10))

    # --------------------------------------------------------
    # STEP 1 — Identify weak competencies
    # --------------------------------------------------------
    targets = _ps_target_concepts(
        learner_profile,
        limit=max(7, number)
    )

    recent = _ps_recent_questions(learner_profile)

    selected = []
    seen_questions = set()

    # --------------------------------------------------------
    # STEP 2 — TARGETED generation
    # --------------------------------------------------------
    for competency in targets:
        candidates = _ps_build_targeted_candidates(
            text,
            competency,
            learner_profile
        )

        mastery = _ps_mastery_value(
            learner_profile,
            competency
        )

        difficulty = _ps_targeted_difficulty(
            learner_profile,
            competency
        )

        for candidate in candidates:
            question_text_value = str(
                candidate.get("question", "")
            ).strip()

            normalized_question = _ps_normalize_concept(
                question_text_value
            )

            # Never repeat a recent question.
            duplicate_recent = False

            for old in recent:
                old_text = _ps_normalize_concept(
                    old.get("question", "")
                )

                if old_text and (
                    old_text == normalized_question
                    or _v24_similarity(
                        old_text,
                        normalized_question
                    ) >= 0.88
                ):
                    duplicate_recent = True
                    break

            if duplicate_recent:
                continue

            if normalized_question in seen_questions:
                continue

            seen_questions.add(normalized_question)

            candidate["personalization"] = {
                "target_competency": competency,
                "current_mastery": round(mastery, 1),
                "reason": (
                    "Targeted because this competency has low mastery."
                    if mastery < 50
                    else
                    "Targeted for adaptive competency reinforcement."
                ),
                "recommended_difficulty": difficulty,
                "exam_target": learner_profile.get("exam_target"),
            }

            # Explicit machine-readable fields for frontend.
            candidate["target_competency"] = competency
            candidate["mastery_before"] = round(mastery, 1)
            candidate["adaptive_reason"] = (
                "LOW_MASTERY"
                if mastery < 50
                else "REINFORCEMENT"
            )

            selected.append(candidate)

            if len(selected) >= number:
                break

        if len(selected) >= number:
            break

    # --------------------------------------------------------
    # STEP 3 — Generic fallback
    #
    # Only use this if the material does not contain enough
    # evidence for the learner's weak competencies.
    # --------------------------------------------------------
    if len(selected) < number:
        remaining = number - len(selected)

        pool = generate_questions(
            text,
            number=max(remaining * 3, 10),
            analysis=analysis,
            retrieval_context=retrieval_context,
        )

        for candidate in pool:
            question_text_value = str(
                candidate.get("question", "")
            ).strip()

            normalized_question = _ps_normalize_concept(
                question_text_value
            )

            if normalized_question in seen_questions:
                continue

            duplicate_recent = False

            for old in recent:
                old_text = _ps_normalize_concept(
                    old.get("question", "")
                )

                if old_text and (
                    old_text == normalized_question
                    or _v24_similarity(
                        old_text,
                        normalized_question
                    ) >= 0.88
                ):
                    duplicate_recent = True
                    break

            if duplicate_recent:
                continue

            seen_questions.add(normalized_question)

            concept = str(
                candidate.get("concept", "General Concepts")
            )

            mastery = _ps_mastery_value(
                learner_profile,
                concept
            )

            candidate["personalization"] = {
                "target_competency": concept,
                "current_mastery": round(mastery, 1),
                "reason": (
                    "Fallback generated from available learning evidence."
                ),
                "recommended_difficulty":
                    _ps_targeted_difficulty(
                        learner_profile,
                        concept
                    ),
                "exam_target":
                    learner_profile.get("exam_target"),
            }

            candidate["target_competency"] = concept
            candidate["mastery_before"] = round(mastery, 1)
            candidate["adaptive_reason"] = "EVIDENCE_FALLBACK"

            selected.append(candidate)

            if len(selected) >= number:
                break

    # --------------------------------------------------------
    # STEP 4 — Final ranking
    #
    # Weakest competency questions always come first.
    # --------------------------------------------------------
    def personalization_rank(question):
        mastery = _ps_float(
            question.get("mastery_before"),
            50
        )

        # Lower mastery = higher priority.
        return (
            -mastery,
            0 if question.get("adaptive_reason") == "LOW_MASTERY" else 1
        )

    selected.sort(key=personalization_rank)

    # --------------------------------------------------------
    # STEP 5 — Final metadata
    # --------------------------------------------------------
    for index, question in enumerate(selected):
        question["personalization"]["rank"] = index + 1

        # Make the competency explicit for downstream mastery updates.
        question["competency"] = question.get(
            "target_competency",
            question.get("concept", "General Concepts")
        )

    return selected[:number]


class PersonalizedQuestionIntelligenceEngine:
    generate_personalized_quiz = staticmethod(
        generate_personalized_quiz
    )

# ============================================================
# PAPERSCOPE V25.1 — TARGETED EVIDENCE MCQ FALLBACK
# ============================================================

def _ps_make_targeted_mcq(competency, evidence, all_concepts, difficulty="medium"):
    """
    Build a competency-specific MCQ directly from evidence when the
    general question validators cannot produce enough questions.
    """

    evidence = str(evidence or "").strip()
    competency = str(competency or "").strip()

    if not evidence or not competency:
        return None

    lower = evidence.lower()

    # --------------------------------------------------------
    # Definition-style question
    # --------------------------------------------------------
    definition_patterns = [
        f"{competency.lower()} is ",
        f"{competency.lower()} refers to ",
        f"{competency.lower()} measures ",
        f"{competency.lower()} describes ",
        f"{competency.lower()} represents ",
    ]

    answer = None

    for pattern in definition_patterns:
        if pattern in lower:
            idx = lower.find(pattern)
            original_idx = idx + len(pattern)
            answer = evidence[original_idx:].strip()
            break

    # If the evidence contains the competency but not an exact
    # definition pattern, use the full evidence as the answer.
    if not answer:
        answer = evidence.strip()

    # Remove trailing sentences where possible.
    answer = answer.split(".")[0].strip()

    if len(answer.split()) < 3:
        return None

    # --------------------------------------------------------
    # Build plausible distractors from other concepts.
    # --------------------------------------------------------
    distractors = []

    for concept in all_concepts:
        concept = str(concept or "").strip()

        if not concept:
            continue

        if _ps_normalize_concept(concept) == _ps_normalize_concept(
            competency
        ):
            continue

        if concept not in distractors:
            distractors.append(
                f"{concept} as a general statistical concept"
            )

        if len(distractors) >= 3:
            break

    # Add controlled generic distractors if needed.
    generic = [
        "A method for storing observations without analyzing them",
        "A process used only to calculate the size of a dataset",
        "A technique that does not depend on uncertainty or evidence",
        "A method used exclusively for presenting statistical results",
    ]

    for item in generic:
        if item not in distractors:
            distractors.append(item)

        if len(distractors) >= 3:
            break

    if len(distractors) < 3:
        return None

    question = {
        "question": (
            f"Which statement best describes {competency} "
            f"according to the learning material?"
        ),
        "answer": answer,
        "distractors": distractors[:3],
        "concept": competency,
        "question_type": "targeted_concept",
        "difficulty": difficulty,
        "evidence": evidence,
    }

    return question


def _ps_targeted_question_variants(
    competency,
    evidence_sentences,
    all_concepts,
    difficulty
):
    """
    Generate multiple targeted variants for the same weak competency.
    """

    results = []

    if not evidence_sentences:
        return results

    evidence = " ".join(evidence_sentences)

    # --------------------------------------------------------
    # Variant 1 — direct concept
    # --------------------------------------------------------
    q = _ps_make_targeted_mcq(
        competency,
        evidence,
        all_concepts,
        difficulty
    )

    if q:
        results.append(q)

    # --------------------------------------------------------
    # Variant 2 — evidence recognition
    # --------------------------------------------------------
    if len(evidence_sentences) >= 1:
        sentence = evidence_sentences[0]

        q = {
            "question": (
                f"A learner is studying {competency}. "
                f"Which statement from the material is most directly "
                f"associated with this competency?"
            ),
            "answer": sentence.strip(),
            "distractors": [],
            "concept": competency,
            "question_type": "targeted_evidence",
            "difficulty": difficulty,
            "evidence": sentence,
        }

        # Create distractors from other evidence sentences.
        for other in evidence_sentences[1:]:
            if (
                other.strip()
                and _ps_normalize_concept(other)
                != _ps_normalize_concept(sentence)
            ):
                q["distractors"].append(other.strip())

            if len(q["distractors"]) >= 3:
                break

        if len(q["distractors"]) < 3:
            for concept in all_concepts:
                if (
                    _ps_normalize_concept(concept)
                    != _ps_normalize_concept(competency)
                ):
                    q["distractors"].append(
                        f"The material's discussion of {concept}"
                    )

                if len(q["distractors"]) >= 3:
                    break

        if len(q["distractors"]) >= 3:
            results.append(q)

    # --------------------------------------------------------
    # Variant 3 — application framing
    # --------------------------------------------------------
    if len(evidence_sentences) >= 1:
        q = {
            "question": (
                f"Which situation would most directly require "
                f"understanding {competency}?"
            ),
            "answer": evidence_sentences[0].strip(),
            "distractors": [],
            "concept": competency,
            "question_type": "targeted_application",
            "difficulty": difficulty,
            "evidence": evidence_sentences[0],
        }

        for concept in all_concepts:
            if (
                _ps_normalize_concept(concept)
                != _ps_normalize_concept(competency)
            ):
                q["distractors"].append(
                    f"A situation focused primarily on {concept}"
                )

            if len(q["distractors"]) >= 3:
                break

        if len(q["distractors"]) >= 3:
            results.append(q)

    return results


def _legacy_generate_personalized_quiz_v25_2(
    text,
    learner_profile=None,
    number=10,
    analysis=None,
    retrieval_context=None,
):
    """
    V25.1 targeted PaperScope quiz engine.

    Weak competencies are the PRIMARY source of questions.
    Generic generation is used only when the material contains
    insufficient evidence for the learner's weak areas.
    """

    learner_profile = learner_profile or {}
    number = max(1, int(number or 10))

    targets = _ps_target_concepts(
        learner_profile,
        limit=max(7, number)
    )

    recent = _ps_recent_questions(learner_profile)

    # Concepts available in the material.
    try:
        best = _v24_best_concepts(text, analysis)
    except Exception:
        best = []

    all_concepts = []

    for item in best or []:
        if isinstance(item, dict) and item.get("concept"):
            all_concepts.append(str(item["concept"]))

    for target in targets:
        if target not in all_concepts:
            all_concepts.append(target)

    selected = []
    seen = set()

    # --------------------------------------------------------
    # PRIMARY PATH: weak competency → evidence → questions
    # --------------------------------------------------------
    for competency in targets:

        mastery = _ps_mastery_value(
            learner_profile,
            competency
        )

        difficulty = _ps_targeted_difficulty(
            learner_profile,
            competency
        )

        evidence_sentences = _ps_targeted_evidence(
            text,
            competency
        )

        if not evidence_sentences:
            continue

        candidates = []

        # First try the sophisticated existing generators.
        try:
            candidates.extend(
                _ps_build_targeted_candidates(
                    text,
                    competency,
                    learner_profile
                )
            )
        except Exception:
            pass

        # If those fail, use our targeted evidence fallback.
        candidates.extend(
            _ps_targeted_question_variants(
                competency,
                evidence_sentences,
                all_concepts,
                difficulty
            )
        )

        for question in candidates:

            stem = _ps_normalize_concept(
                question.get("question", "")
            )

            if not stem or stem in seen:
                continue

            # Recent-question protection.
            repeated = False

            for old in recent:
                old_stem = _ps_normalize_concept(
                    old.get("question", "")
                )

                if old_stem and (
                    old_stem == stem
                    or _v24_similarity(old_stem, stem) >= 0.88
                ):
                    repeated = True
                    break

            if repeated:
                continue

            seen.add(stem)

            question["competency"] = competency
            question["target_competency"] = competency
            question["mastery_before"] = round(mastery, 1)

            question["personalization"] = {
                "rank": len(selected) + 1,
                "target_competency": competency,
                "current_mastery": round(mastery, 1),
                "reason": (
                    "Targeted because this competency has low mastery."
                    if mastery < 50
                    else "Targeted for competency reinforcement."
                ),
                "recommended_difficulty": difficulty,
                "exam_target": learner_profile.get("exam_target"),
            }

            question["adaptive_reason"] = (
                "LOW_MASTERY"
                if mastery < 50
                else "REINFORCEMENT"
            )

            selected.append(question)

            if len(selected) >= number:
                return selected[:number]

    # --------------------------------------------------------
    # IMPORTANT:
    # Do NOT immediately fall back to generic high-mastery
    # questions. First attempt to distribute targeted questions
    # across all weak competencies.
    # --------------------------------------------------------
    if len(selected) < number:

        for competency in targets:

            if len(selected) >= number:
                break

            mastery = _ps_mastery_value(
                learner_profile,
                competency
            )

            difficulty = _ps_targeted_difficulty(
                learner_profile,
                competency
            )

            evidence_sentences = _ps_targeted_evidence(
                text,
                competency
            )

            for sentence in evidence_sentences:

                # Generate a simple but explicitly targeted
                # comprehension question.
                q = {
                    "question": (
                        f"According to the material, which statement "
                        f"is associated with {competency}?"
                    ),
                    "answer": sentence.strip(),
                    "distractors": [],
                    "concept": competency,
                    "competency": competency,
                    "target_competency": competency,
                    "mastery_before": round(mastery, 1),
                    "question_type": "targeted_comprehension",
                    "difficulty": difficulty,
                    "evidence": sentence.strip(),
                    "adaptive_reason": (
                        "LOW_MASTERY"
                        if mastery < 50
                        else "REINFORCEMENT"
                    ),
                    "personalization": {
                        "rank": len(selected) + 1,
                        "target_competency": competency,
                        "current_mastery": round(mastery, 1),
                        "reason": (
                            "Targeted because this competency "
                            "has low mastery."
                            if mastery < 50
                            else "Targeted for competency reinforcement."
                        ),
                        "recommended_difficulty": difficulty,
                        "exam_target":
                            learner_profile.get("exam_target"),
                    },
                }

                # Use other competencies as controlled distractors.
                for other in all_concepts:
                    if (
                        _ps_normalize_concept(other)
                        != _ps_normalize_concept(competency)
                    ):
                        q["distractors"].append(
                            f"A statement primarily about {other}"
                        )

                    if len(q["distractors"]) >= 3:
                        break

                if len(q["distractors"]) < 3:
                    continue

                stem = _ps_normalize_concept(q["question"])

                if stem in seen:
                    continue

                seen.add(stem)
                selected.append(q)

                if len(selected) >= number:
                    break

    # --------------------------------------------------------
    # Only now use generic fallback.
    # --------------------------------------------------------
    if len(selected) < number:

        pool = generate_questions(
            text,
            number=max(number * 2, 10),
            analysis=analysis,
            retrieval_context=retrieval_context,
        )

        for q in pool:

            if len(selected) >= number:
                break

            stem = _ps_normalize_concept(
                q.get("question", "")
            )

            if stem in seen:
                continue

            concept = str(
                q.get("concept", "General Concepts")
            )

            mastery = _ps_mastery_value(
                learner_profile,
                concept
            )

            # Prefer lower mastery even in fallback.
            q["competency"] = concept
            q["target_competency"] = concept
            q["mastery_before"] = round(mastery, 1)
            q["adaptive_reason"] = "EVIDENCE_FALLBACK"

            q["personalization"] = {
                "rank": len(selected) + 1,
                "target_competency": concept,
                "current_mastery": round(mastery, 1),
                "reason": "Fallback from available material evidence.",
                "recommended_difficulty":
                    _ps_targeted_difficulty(
                        learner_profile,
                        concept
                    ),
                "exam_target":
                    learner_profile.get("exam_target"),
            }

            selected.append(q)
            seen.add(stem)

    # --------------------------------------------------------
    # Final ordering: weakest competencies first.
    # --------------------------------------------------------
    selected.sort(
        key=lambda q: (
            _ps_float(q.get("mastery_before"), 50),
            q.get("personalization", {}).get("rank", 999)
        )
    )

    for index, q in enumerate(selected):
        q.setdefault("personalization", {})
        q["personalization"]["rank"] = index + 1

    return selected[:number]


class PersonalizedQuestionIntelligenceEngine:
    generate_personalized_quiz = staticmethod(
        generate_personalized_quiz
    )
