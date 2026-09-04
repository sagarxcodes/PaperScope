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








# ============================================================
# PaperScope Question Intelligence Engine v23
# Standard exam-quality, source-grounded MCQ generation
# ============================================================

def _norm_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _tokens(value):
    return set(re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", value.lower()))


def _similarity(a, b):
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def _unique_clean(items):
    out = []
    seen = set()

    for item in items:
        item = _norm_text(item)
        key = item.lower()

        if not item or key in seen:
            continue

        seen.add(key)
        out.append(item)

    return out


def _sentence_pool(text):
    return [
        _norm_text(x)
        for x in split_sentences(text)
        if len(_norm_text(x).split()) >= 5
    ]


def _find_definition(sentence):
    patterns = [
        r"^(.+?)\s+(?:is|are|refers to|means|can be defined as)\s+(.+?)(?:[.!?]|$)",
        r"^(.+?)\s+(?:is|are)\s+defined as\s+(.+?)(?:[.!?]|$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, sentence, re.I)
        if m:
            subject = _norm_text(m.group(1))
            definition = _norm_text(m.group(2))

            if 1 <= len(subject.split()) <= 10 and len(definition.split()) >= 3:
                return subject, definition

    return None, None


def _extract_relation(sentence):
    patterns = [
        r"(.+?)\s+(?:includes|include|contains|contain|consists of|comprises)\s+(.+)",
        r"(.+?)\s+(?:uses|use|combines|combine)\s+(.+)",
        r"(.+?)\s+(?:helps|help|allows|allow|enables|enable)\s+(.+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, sentence, re.I)
        if m:
            subject = _norm_text(m.group(1))
            relation = _norm_text(m.group(2)).rstrip(".")
            if len(subject.split()) <= 12 and len(relation.split()) >= 2:
                return subject, relation

    return None, None


def _extract_statements(sentences):
    records = []

    for sentence in sentences:
        subject, definition = _find_definition(sentence)
        relation_subject, relation_value = _extract_relation(sentence)

        records.append({
            "sentence": sentence,
            "definition_subject": subject,
            "definition": definition,
            "relation_subject": relation_subject,
            "relation_value": relation_value,
        })

    return records


def _concept_name(concept):
    if isinstance(concept, dict):
        return _norm_text(
            concept.get("concept")
            or concept.get("name")
            or concept.get("term")
        )
    return _norm_text(concept)


def _concepts_from_analysis(analysis):
    concepts = []

    if not isinstance(analysis, dict):
        return concepts

    for item in analysis.get("concepts", []):
        name = _concept_name(item)
        if name:
            concepts.append(item)

    return concepts


def _concept_names(analysis):
    return _unique_clean([
        _concept_name(x)
        for x in _concepts_from_analysis(analysis)
        if _concept_name(x)
    ])


def _concept_for_sentence(sentence, analysis):
    names = _concept_names(analysis)
    low = sentence.lower()

    ranked = []

    for name in names:
        score = 0
        nlow = name.lower()

        if nlow in low:
            score += 10

        score += len(_tokens(name) & _tokens(sentence))

        ranked.append((score, name))

    ranked.sort(reverse=True)

    return ranked[0][1] if ranked and ranked[0][0] > 0 else None


def _best_distractors(answer, pool, count=3, same_category=None):
    """
    Distractors are selected from concepts/statements actually found
    in the source material. Generic unrelated artifacts are forbidden.
    """
    answer = _norm_text(answer)

    scored = []

    for candidate in _unique_clean(pool):
        if candidate.lower() == answer.lower():
            continue

        # Reject extremely similar candidates.
        sim = _similarity(answer, candidate)

        if sim >= 0.80:
            continue

        score = 0

        # Prefer candidates with comparable length.
        diff = abs(len(candidate.split()) - len(answer.split()))
        score += max(0, 4 - diff)

        # Prefer semantic similarity without being duplicates.
        score += sim * 3

        # Avoid answers containing one another when that makes
        # the question trivially solvable.
        al = answer.lower()
        cl = candidate.lower()

        if al in cl or cl in al:
            score -= 5

        scored.append((score, candidate))

    scored.sort(key=lambda x: x[0], reverse=True)

    result = []
    for _, candidate in scored:
        if all(_similarity(candidate, existing) < 0.75 for existing in result):
            result.append(candidate)

        if len(result) == count:
            break

    return result


def _statement_candidates(records, field):
    values = []

    for record in records:
        value = record.get(field)
        if value:
            values.append(value)

    return _unique_clean(values)


def _make_definition_candidate(record, analysis):
    subject = record.get("definition_subject")
    definition = record.get("definition")

    if not subject or not definition:
        return None

    concepts = _concept_names(analysis)

    distractors = _best_distractors(
        subject,
        concepts,
        3
    )

    if len(distractors) < 3:
        return None

    return {
        "question": f"Which of the following best describes {subject}?",
        "answer_text": subject,
        "options": distractors,
        "evidence": record["sentence"],
        "question_type": "definition",
        "difficulty": "easy",
    }


def _make_relationship_candidate(record, analysis, records):
    subject = record.get("relation_subject")
    value = record.get("relation_value")

    if not subject or not value:
        return None

    values = _statement_candidates(records, "relation_value")

    distractors = _best_distractors(value, values, 3)

    if len(distractors) < 3:
        return None

    return {
        "question": f"According to the source material, which statement is associated with {subject}?",
        "answer_text": value,
        "options": distractors,
        "evidence": record["sentence"],
        "question_type": "relationship",
        "difficulty": "medium",
    }


def _make_concept_candidate(sentence, analysis):
    concept = _concept_for_sentence(sentence, analysis)

    if not concept:
        return None

    concepts = _concept_names(analysis)

    distractors = _best_distractors(concept, concepts, 3)

    if len(distractors) < 3:
        return None

    return {
        "question": (
            f"Which concept is most directly represented by the following "
            f"description?\n\n{sentence}"
        ),
        "answer_text": concept,
        "options": distractors,
        "evidence": sentence,
        "question_type": "concept",
        "difficulty": "medium",
    }


def _make_application_candidate(sentence, analysis):
    concept = _concept_for_sentence(sentence, analysis)

    if not concept:
        return None

    concepts = _concept_names(analysis)
    distractors = _best_distractors(concept, concepts, 3)

    if len(distractors) < 3:
        return None

    return {
        "question": (
            f"A learner encounters the situation described below. "
            f"Which concept should the learner identify as the most relevant?\n\n"
            f"{sentence}"
        ),
        "answer_text": concept,
        "options": distractors,
        "evidence": sentence,
        "question_type": "application",
        "difficulty": "medium",
    }


def _make_scenario_candidate(sentence, analysis):
    concept = _concept_for_sentence(sentence, analysis)

    if not concept:
        return None

    concepts = _concept_names(analysis)
    distractors = _best_distractors(concept, concepts, 3)

    if len(distractors) < 3:
        return None

    return {
        "question": (
            f"Consider a real-world case in which the following situation "
            f"occurs:\n\n{sentence}\n\n"
            f"Which PaperScope concept best explains this case?"
        ),
        "answer_text": concept,
        "options": distractors,
        "evidence": sentence,
        "question_type": "scenario",
        "difficulty": "hard",
    }


def _make_comparison_candidate(analysis):
    names = _concept_names(analysis)

    if len(names) < 4:
        return None

    a, b = names[0], names[1]
    distractors = _best_distractors(a, names[2:], 3)

    if len(distractors) < 3:
        return None

    return {
        "question": (
            f"Which of the following concepts is most closely associated "
            f"with the same subject area as {a}, rather than {b}?"
        ),
        "answer_text": distractors[0],
        "options": [
            distractors[0],
            a,
            b,
            distractors[1],
        ],
        "evidence": (
            f"The source material identifies {a} and {b} as distinct concepts."
        ),
        "question_type": "comparison",
        "difficulty": "hard",
    }


def _make_interpretation_candidate(sentence, analysis):
    concept = _concept_for_sentence(sentence, analysis)

    if not concept:
        return None

    concepts = _concept_names(analysis)
    distractors = _best_distractors(concept, concepts, 3)

    if len(distractors) < 3:
        return None

    return {
        "question": (
            "What is the most appropriate interpretation of the following "
            f"information from the learning material?\n\n{sentence}"
        ),
        "answer_text": concept,
        "options": distractors,
        "evidence": sentence,
        "question_type": "interpretation",
        "difficulty": "hard",
    }


def _build_final_question(candidate, index, topic=None):
    answer = _norm_text(candidate["answer_text"])
    distractors = _unique_clean(candidate.get("options", []))

    if len(distractors) != 3:
        return None

    options = [answer] + distractors

    # Deterministic shuffle so repeated API calls remain reproducible.
    rng = random.Random(1000 + index)
    rng.shuffle(options)

    answer_index = options.index(answer)

    if len(set(x.lower() for x in options)) != 4:
        return None

    if not candidate.get("evidence"):
        return None

    evidence = _norm_text(candidate["evidence"])

    return {
        "id": f"PS-Q{index + 1}",
        "question": _norm_text(candidate["question"]),
        "options": options,
        "answer": answer_index,
        "correct": answer,
        "correct_answer": answer,
        "explanation": (
            f"The correct answer is {answer}. "
            f"This is supported by the source evidence: {evidence}"
        ),
        "evidence": evidence,
        "source_sentence": evidence,
        "concept": _concept_for_sentence(evidence, {"concepts": [{"concept": answer}]}),
        "topic": topic or "General Concepts",
        "difficulty": candidate.get("difficulty", "medium"),
        "question_type": candidate.get("question_type", "concept"),
    }


def _quality_score(question):
    score = 0

    q = question.get("question", "")
    options = question.get("options", [])

    if len(q.split()) >= 8:
        score += 2

    if len(options) == 4:
        score += 3

    if question.get("evidence"):
        score += 3

    if question.get("question_type") in {
        "application",
        "scenario",
        "comparison",
        "interpretation",
        "relationship",
    }:
        score += 3

    if question.get("difficulty") == "hard":
        score += 2
    elif question.get("difficulty") == "medium":
        score += 1

    # Penalize giveaway questions.
    lowq = q.lower()
    if "according to the source material" in lowq:
        score -= 1

    return score


def _diversify_questions(questions, number):
    if not questions:
        return []

    preferred_order = [
        "concept",
        "application",
        "scenario",
        "comparison",
        "relationship",
        "interpretation",
        "definition",
    ]

    selected = []
    used_types = Counter()
    used_answers = set()

    ranked = sorted(
        questions,
        key=_quality_score,
        reverse=True
    )

    # First pass: maximize type diversity.
    for qtype in preferred_order:
        candidates = [
            q for q in ranked
            if q.get("question_type") == qtype
            and q.get("correct", "").lower() not in used_answers
        ]

        if candidates:
            q = candidates[0]
            selected.append(q)
            used_types[qtype] += 1
            used_answers.add(q.get("correct", "").lower())

            if len(selected) >= number:
                return selected

    # Second pass: fill remaining slots while limiting repetition.
    for q in ranked:
        if q in selected:
            continue

        answer = q.get("correct", "").lower()
        qtype = q.get("question_type", "concept")

        if answer in used_answers:
            continue

        if used_types[qtype] >= 2:
            continue

        selected.append(q)
        used_types[qtype] += 1
        used_answers.add(answer)

        if len(selected) >= number:
            return selected

    # Final fallback.
    for q in ranked:
        if q not in selected:
            selected.append(q)

        if len(selected) >= number:
            break

    return selected


def create_question(
    concept_data,
    evidence,
    question_type=None,
    difficulty=None,
    concept_alternatives=None,
):
    """
    Compatibility wrapper.

    Older callers can still request a question directly, while v23 uses
    source-grounded distractors instead of generic hardcoded distractors.
    """
    concept = _concept_name(concept_data)

    if not concept:
        return None

    alternatives = _unique_clean(concept_alternatives or [])

    if len(alternatives) < 3:
        return None

    candidate = {
        "question": (
            f"Which of the following is most directly associated with {concept}?"
        ),
        "answer_text": concept,
        "options": _best_distractors(concept, alternatives, 3),
        "evidence": _norm_text(evidence),
        "question_type": question_type or "concept",
        "difficulty": difficulty or "medium",
    }

    if len(candidate["options"]) < 3:
        return None

    return _build_final_question(candidate, 0)


def generate_questions(text, number=10, analysis=None):
    """
    Main v23 question generator.

    Pipeline:
        source material
        -> evidence extraction
        -> concept grounding
        -> question blueprints
        -> source-derived distractors
        -> validation
        -> diversified final MCQs
    """
    text = _norm_text(text)

    if not text:
        return []

    number = max(1, int(number or 10))

    if analysis is None:
        analysis = build_concept_analysis(text)

    sentences = _sentence_pool(text)

    if not sentences:
        return []

    records = _extract_statements(sentences)

    candidates = []

    # Definition questions.
    for record in records:
        candidate = _make_definition_candidate(record, analysis)
        if candidate:
            candidates.append(candidate)

    # Relationship / inclusion questions.
    for record in records:
        candidate = _make_relationship_candidate(record, analysis, records)
        if candidate:
            candidates.append(candidate)

    # Concept understanding.
    for sentence in sentences:
        candidate = _make_concept_candidate(sentence, analysis)
        if candidate:
            candidates.append(candidate)

    # Application questions.
    for sentence in sentences:
        candidate = _make_application_candidate(sentence, analysis)
        if candidate:
            candidates.append(candidate)

    # Scenario questions.
    for sentence in sentences:
        if len(sentence.split()) >= 10:
            candidate = _make_scenario_candidate(sentence, analysis)
            if candidate:
                candidates.append(candidate)

    # Interpretation questions.
    for sentence in sentences:
        if len(sentence.split()) >= 12:
            candidate = _make_interpretation_candidate(sentence, analysis)
            if candidate:
                candidates.append(candidate)

    # Comparison only when the source has enough concepts.
    comparison = _make_comparison_candidate(analysis)
    if comparison:
        candidates.append(comparison)

    # Remove duplicate stems.
    unique_candidates = []
    seen_stems = set()

    for candidate in candidates:
        stem = _norm_text(candidate["question"]).lower()

        if stem in seen_stems:
            continue

        seen_stems.add(stem)
        unique_candidates.append(candidate)

    final = []

    for i, candidate in enumerate(unique_candidates):
        q = _build_final_question(
            candidate,
            i,
            topic=(
                analysis.get("topics", ["General Concepts"])[0]
                if isinstance(analysis, dict)
                and analysis.get("topics")
                else "General Concepts"
            ),
        )

        if q:
            final.append(q)

    final = _diversify_questions(final, number)

    # Re-number after diversification.
    for i, question in enumerate(final):
        question["id"] = f"PS-Q{i + 1}"

    return final[:number]


def generate_questions_from_analysis(analysis, text=None, number=10):
    """
    Compatibility API for callers that already possess concept analysis.
    """
    if text:
        return generate_questions(
            text=text,
            number=number,
            analysis=analysis,
        )

    if not isinstance(analysis, dict):
        return []

    source = analysis.get("source_text") or analysis.get("text") or ""

    if source:
        return generate_questions(
            text=source,
            number=number,
            analysis=analysis,
        )

    return []


class QuestionIntelligenceEngine:
    generate_questions = staticmethod(generate_questions)
    generate_questions_from_analysis = staticmethod(generate_questions_from_analysis)
    create_question = staticmethod(create_question)
    build_concept_analysis = staticmethod(build_concept_analysis)
