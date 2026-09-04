import re
import math
from collections import Counter, defaultdict


class MaterialIntelligenceEngine:

    STOPWORDS = {
        "the", "and", "for", "with", "that", "this", "from",
        "are", "was", "were", "has", "have", "into", "their",
        "there", "which", "where", "when", "what", "will",
        "can", "may", "than", "then", "also", "been", "being",
        "about", "such", "using", "used", "each", "more",
        "most", "other", "these", "those", "between", "through",
        "during", "only", "not", "but", "its", "our", "your",
        "they", "them", "you", "who", "how", "why",
        "lecture", "slide", "page", "chapter", "section",
        "introduction", "contents",
        "above", "shown", "show", "shows", "following",
        "given", "example", "examples", "using", "used",
        "make", "makes", "made", "like", "also",
        "half", "full", "inputs", "output", "outputs",
        "define", "defined", "definition"
    }

    TOPIC_KEYWORDS = {
        "Survey Methodology": [
            "survey", "sampling", "sample", "sampling frame",
            "questionnaire", "population", "respondent",
            "enumeration", "field survey"
        ],
        "Statistical Methods": [
            "mean", "median", "mode", "variance",
            "standard deviation", "regression", "hypothesis",
            "statistical", "distribution", "correlation"
        ],
        "Probability": [
            "probability", "random", "event", "outcome",
            "conditional probability", "bayes", "independent"
        ],
        "Data Analysis": [
            "data analysis", "dataset", "analysis",
            "visualization", "trend", "interpretation",
            "descriptive statistics"
        ],
        "Official Statistics": [
            "official statistics", "census", "government",
            "national statistics", "statistical system",
            "indicator", "economic statistics"
        ],
        "Research Methods": [
            "research", "methodology", "research design",
            "qualitative", "quantitative", "experiment",
            "observation"
        ],

        "Computer Systems": [
            "computer system", "computing system", "computer",
            "cpu", "processor", "memory", "hardware",
            "nand", "tetris", "digital circuit"
        ],

        "Boolean Logic": [
            "boolean", "boolean function", "boolean functions",
            "boolean algebra", "boolean operation",
            "boolean operations", "truth table", "logic gate",
            "and gate", "or gate", "not gate",
            "nand", "nor", "xor", "xnor",
            "logical operation", "digital logic"
        ],

        "Digital Circuits": [
            "digital circuit", "digital circuits",
            "logic circuit", "logic circuits",
            "half adder", "full adder", "adder",
            "combinational circuit", "circuit synthesis",
            "hardware circuit"
        ]
    }

    CONCEPT_PHRASES = [
        "official statistics",
        "statistical system",
        "sampling frame",
        "simple random sampling",
        "data collection",
        "data analysis",
        "descriptive statistics",
        "inferential statistics",
        "standard deviation",
        "hypothesis testing",
        "probability distribution",
        "conditional probability",
        "research design",
        "survey methodology",
        "data quality",
        "economic statistics",
        "social statistics",
        "population parameter",
        "sample statistic",

        # Computing / Boolean Logic
        "boolean function",
        "boolean functions",
        "boolean algebra",
        "boolean operation",
        "boolean operations",
        "truth table",
        "logic gate",
        "logic gates",
        "and gate",
        "or gate",
        "not gate",
        "nand gate",
        "nor gate",
        "xor gate",
        "xnor gate",
        "half adder",
        "full adder",
        "digital circuit",
        "digital circuits",
        "circuit synthesis",
        "combinational circuit"
    ]

    def clean_text(self, text: str) -> str:
        text = text or ""
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[^\w\s.,;:%()\-=/+\n]", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def extract_sentences(self, text: str):
        sentences = re.split(r"(?<=[.!?])\s+", text)

        return [
            re.sub(r"\s+", " ", sentence).strip()
            for sentence in sentences
            if len(sentence.strip().split()) >= 5
        ]

    def split_units(self, text: str):
        """
        Creates analysis units.

        If page markers exist, each page becomes a unit.
        Otherwise paragraphs become units.
        """

        page_pattern = re.compile(
            r"(?:^|\n)\s*(?:page\s*)?(\d{1,4})\s*[:.)-]\s*",
            re.I
        )

        matches = list(page_pattern.finditer(text))

        if len(matches) >= 2:
            units = []

            for i, match in enumerate(matches):
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

                content = text[start:end].strip()

                if content:
                    units.append({
                        "unit": i + 1,
                        "type": "page",
                        "content": content
                    })

            if units:
                return units

        paragraphs = [
            p.strip()
            for p in re.split(r"\n\s*\n", text)
            if len(p.strip().split()) >= 5
        ]

        if len(paragraphs) >= 2:
            return [
                {
                    "unit": i + 1,
                    "type": "section",
                    "content": paragraph
                }
                for i, paragraph in enumerate(paragraphs)
            ]

        sentences = self.extract_sentences(text)

        return [
            {
                "unit": i + 1,
                "type": "sentence_group",
                "content": sentence
            }
            for i, sentence in enumerate(sentences)
        ]

    def classify_material(self, text: str):
        lowered = text.lower()

        signals = {
            "pyq": [
                "previous year question",
                "previous year questions",
                "pyq",
                "question paper",
                "marks",
                "choose the correct",
                "multiple choice question",
                "mcq",
                "section a",
                "section b"
            ],
            "lecture": [
                "lecture",
                "learning objectives",
                "objective",
                "introduction",
                "slide",
                "slides",
                "key takeaway",
                "department of computer science",
                "course",
                "syllabus",
                "chapter",
                "example",
                "boolean functions",
                "boolean algebra",
                "logic gates"
            ],
            "notes": [
                "notes",
                "summary",
                "revision",
                "important points",
                "key points"
            ]
        }

        scores = {
            material_type: sum(
                lowered.count(signal)
                for signal in indicators
            )
            for material_type, indicators in signals.items()
        }

        active = {
            key: value
            for key, value in scores.items()
            if value > 0
        }

        if not active:
            return "general", scores

        ordered = sorted(
            active.items(),
            key=lambda item: item[1],
            reverse=True
        )

        if len(ordered) >= 2:
            top_score = ordered[0][1]
            second_score = ordered[1][1]

            if second_score >= max(1, top_score * 0.6):
                return "mixed", scores

        return ordered[0][0], scores

    def detect_topics(self, text: str):
        lowered = text.lower()

        scores = {}

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                occurrences = len(
                    re.findall(
                        rf"\b{re.escape(keyword.lower())}\b",
                        lowered
                    )
                )
                score += occurrences

            if score:
                scores[topic] = score

        total = sum(scores.values())

        if not total:
            return []

        topics = []

        for topic, score in sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True
        ):
            topics.append({
                "topic": topic,
                "mentions": score,
                "weightage": round((score / total) * 100, 1)
            })

        return topics

    def extract_candidate_terms(self, text: str):
        lowered = text.lower()

        candidates = []

        # Domain-specific multi-word concepts first.
        for phrase in self.CONCEPT_PHRASES:
            count = len(
                re.findall(
                    rf"\b{re.escape(phrase)}\b",
                    lowered
                )
            )

            if count:
                candidates.append(
                    (phrase, count, "phrase")
                )

        words = re.findall(
            r"\b[a-zA-Z][a-zA-Z\-]{3,}\b",
            lowered
        )

        frequency = Counter(
            word
            for word in words
            if word not in self.STOPWORDS
        )

        for word, count in frequency.items():
            candidates.append(
                (word, count, "term")
            )

        return candidates

    def extract_key_concepts(self, text: str, limit: int = 15):
        candidates = self.extract_candidate_terms(text)

        # Prefer meaningful phrases over generic single words.
        candidates.sort(
            key=lambda item: (
                item[2] == "phrase",
                item[1],
                len(item[0].split())
            ),
            reverse=True
        )

        selected = []
        seen = set()

        for concept, frequency, concept_type in candidates:
            if concept in seen:
                continue

            # Avoid including a single word when it is already
            # represented by a meaningful phrase.
            if concept_type == "term":
                if any(
                    concept in phrase.split()
                    for phrase, _, phrase_type in candidates
                    if phrase_type == "phrase"
                ):
                    continue

            selected.append({
                "concept": concept,
                "frequency": frequency,
                "type": concept_type
            })

            seen.add(concept)

            if len(selected) >= limit:
                break

        return selected

    def concept_evidence(self, units):
        """
        Maps concepts to the units where they actually occur.
        This is the foundation for page/section coverage analysis.
        """

        evidence = defaultdict(list)

        all_concepts = set(self.CONCEPT_PHRASES)

        for unit in units:
            lowered = unit["content"].lower()

            # Known domain phrases.
            for phrase in self.CONCEPT_PHRASES:
                if re.search(
                    rf"\b{re.escape(phrase)}\b",
                    lowered
                ):
                    evidence[phrase].append(unit["unit"])

            # Important single terms.
            words = re.findall(
                r"\b[a-zA-Z][a-zA-Z\-]{4,}\b",
                lowered
            )

            for word in words:
                if word not in self.STOPWORDS:
                    all_concepts.add(word)

        # Add meaningful single-word concepts only when
        # they occur across the actual material.
        for concept in list(all_concepts):
            if concept in evidence:
                continue

            for unit in units:
                if re.search(
                    rf"\b{re.escape(concept)}\b",
                    unit["content"].lower()
                ):
                    evidence[concept].append(unit["unit"])

        return evidence

    def calculate_concept_coverage(self, text, units):
        evidence = self.concept_evidence(units)

        if not units:
            return []

        total_units = len(units)
        total_words = max(1, len(text.split()))

        results = []

        for concept, unit_ids in evidence.items():

            unique_units = sorted(set(unit_ids))

            if not unique_units:
                continue

            concept_text = " ".join(
                units[unit_id - 1]["content"]
                for unit_id in unique_units
                if unit_id <= len(units)
            )

            frequency = len(
                re.findall(
                    rf"\b{re.escape(concept)}\b",
                    text.lower()
                )
            )

            coverage = (
                len(unique_units) / total_units
            ) * 100

            word_share = (
                len(concept_text.split()) / total_words
            ) * 100

            # Importance combines coverage and repetition,
            # rather than using a hard-coded percentage.
            importance = (
                (coverage * 0.65) +
                (min(frequency, 10) / 10 * 35)
            )

            results.append({
                "concept": concept,
                "frequency": frequency,
                "units": unique_units,
                "unit_count": len(unique_units),
                "coverage": round(coverage, 1),
                "word_share": round(word_share, 1),
                "importance": round(min(importance, 100), 1)
            })

        results.sort(
            key=lambda item: (
                item["importance"],
                item["frequency"]
            ),
            reverse=True
        )

        # Keep concepts that have meaningful evidence.
        return results[:30]

    def derive_weightage(self, concept_coverage):
        """
        Converts concept importance into a normalized distribution.

        The percentages are derived from the actual material and
        therefore sum to approximately 100%.
        """

        if not concept_coverage:
            return []

        raw_total = sum(
            item["importance"]
            for item in concept_coverage
        )

        if raw_total <= 0:
            return []

        result = []

        for item in concept_coverage:
            result.append({
                **item,
                "weightage": round(
                    (item["importance"] / raw_total) * 100,
                    1
                )
            })

        # Fix floating-point rounding drift.
        difference = round(
            100.0 - sum(item["weightage"] for item in result),
            1
        )

        if result:
            result[0]["weightage"] = round(
                result[0]["weightage"] + difference,
                1
            )

        return result

    def extract_subconcepts(self, concept_coverage, limit=5):
        """
        Finds related concepts appearing in the same evidence units.
        """

        subconcepts = []

        for item in concept_coverage[:limit]:

            related = []

            for candidate in concept_coverage:
                if candidate["concept"] == item["concept"]:
                    continue

                overlap = len(
                    set(item["units"]) &
                    set(candidate["units"])
                )

                if overlap:
                    related.append(
                        (
                            candidate["concept"],
                            overlap
                        )
                    )

            related.sort(
                key=lambda pair: pair[1],
                reverse=True
            )

            subconcepts.append({
                "concept": item["concept"],
                "sub_concepts": [
                    name
                    for name, _ in related[:5]
                ]
            })

        return subconcepts

    def estimate_complexity(self, text: str):
        words = text.split()

        if not words:
            return "low"

        avg_word_length = sum(
            len(word.strip(".,;:()"))
            for word in words
        ) / len(words)

        sentences = self.extract_sentences(text)

        avg_sentence_length = (
            len(words) / len(sentences)
            if sentences else len(words)
        )

        if avg_word_length > 6 or avg_sentence_length > 25:
            return "high"

        if avg_word_length > 5 or avg_sentence_length > 17:
            return "medium"

        return "low"

    def learning_signals(self, text: str):
        return {
            "has_definitions": bool(
                re.search(
                    r"\b(is|are|refers to|defined as|means|known as)\b",
                    text,
                    re.I
                )
            ),
            "has_examples": bool(
                re.search(
                    r"\b(example|for instance|such as|e\.g\.)\b",
                    text,
                    re.I
                )
            ),
            "has_formulas": bool(
                re.search(
                    r"(=|∑|√|\bformula\b|\bequation\b)",
                    text,
                    re.I
                )
            ),
            "has_processes": bool(
                re.search(
                    r"\b(first|second|third|next|then|finally|steps?|process)\b",
                    text,
                    re.I
                )
            ),
            "has_comparisons": bool(
                re.search(
                    r"\b(whereas|while|difference|compared|versus|vs\.?)\b",
                    text,
                    re.I
                )
            ),
            "has_lists": bool(
                re.search(
                    r"(?:^|\n)\s*(?:[-•*]|\d+[.)])\s+",
                    text
                )
            )
        }

    def analyze(self, text: str):

        cleaned = self.clean_text(text)

        if not cleaned:
            return {
                "success": False,
                "error": "No readable learning material was found."
            }

        units = self.split_units(cleaned)

        material_type, classifier_scores = self.classify_material(cleaned)

        sentences = self.extract_sentences(cleaned)

        topics = self.detect_topics(cleaned)

        concepts = self.extract_key_concepts(cleaned)

        concept_coverage = self.calculate_concept_coverage(
            cleaned,
            units
        )

        concept_weightage = self.derive_weightage(
            concept_coverage
        )

        subconcepts = self.extract_subconcepts(
            concept_weightage
        )

        word_count = len(cleaned.split())

        return {
            "success": True,
            "engine": "Material Intelligence Engine v2",

            "material": {
                "characters": len(cleaned),
                "words": word_count,
                "sentences": len(sentences),
                "analysis_units": len(units),
                "unit_type": units[0]["type"] if units else "unknown",
                "estimated_complexity": self.estimate_complexity(cleaned)
            },

            "classification": {
                "material_type": material_type,
                "classifier_scores": classifier_scores
            },

            "topics": topics,
            "topic_count": len(topics),

            "key_concepts": concepts,
            "concept_count": len(concepts),

            "concept_analysis": {
                "concepts": concept_weightage,
                "sub_concepts": subconcepts
            },

            "learning_signals": self.learning_signals(cleaned),

            "evidence_map": [
                {
                    "concept": item["concept"],
                    "units": item["units"],
                    "coverage": item["coverage"]
                }
                for item in concept_weightage[:20]
            ]
        }


material_engine = MaterialIntelligenceEngine()
