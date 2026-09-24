"""Syntactic predicate analyzer for Japanese foreshadowing resolution."""

import logging
import re
from typing import List, Optional, Set, Tuple

from src.config.predicate_matrices import (
    RESOLVED_PREDICATES,
    PROGRESSED_PREDICATES,
    MENTION_ONLY_PREDICATES,
)
from src.models.predicate_match import PredicateMatch, PredicateAnalysisResult

logger = logging.getLogger(__name__)

# Sentence splitting pattern (splits by Japanese sentence endings)
SENTENCE_SPLIT_PATTERN = re.compile(r"[^。！？!?\n]+[。！？!?\n]?")


class ForeshadowingPredicateAnalyzer:
    """Analyzes prose sentences containing foreshadowing keywords using Japanese morphology."""

    def __init__(self) -> None:
        self._tokenizer = None
        self._split_mode = None
        self._init_sudachi()

    def _init_sudachi(self) -> None:
        """Initialize SudachiPy tokenizer safely."""
        try:
            from sudachipy import dictionary, tokenizer

            self._tokenizer = dictionary.Dictionary().create()
            self._split_mode = tokenizer.Tokenizer.SplitMode.C
        except Exception as e:
            logger.warning(
                f"SudachiPy not available in ForeshadowingPredicateAnalyzer, fallback regex used: {e}"
            )
            self._tokenizer = None

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        if not text:
            return []
        sentences = [s.strip() for s in SENTENCE_SPLIT_PATTERN.findall(text) if s.strip()]
        return sentences

    def analyze_sentence(
        self, sentence: str, keyword: str
    ) -> List[Tuple[str, str]]:
        """
        Extract predicates related to the keyword in the sentence.

        Returns:
            List of (predicate_dictionary_form, predicate_type)
        """
        extracted_predicates: List[str] = []

        if self._tokenizer:
            try:
                morphemes = self._tokenizer.tokenize(sentence, self._split_mode)
                for i, m in enumerate(morphemes):
                    pos = m.part_of_speech()
                    pos_major = pos[0]
                    pos_sub = pos[1] if len(pos) > 1 else ""

                    # Check for verbs and adjectives (independent)
                    if pos_major in ("動詞", "形容詞") and pos_sub != "非自立":
                        dict_form = m.dictionary_form()
                        # Check compound (e.g. サ変名詞 + する)
                        if i > 0 and morphemes[i - 1].part_of_speech()[0] == "名詞":
                            compound = morphemes[i - 1].surface() + dict_form
                            extracted_predicates.append(compound)
                        extracted_predicates.append(dict_form)
            except Exception as e:
                logger.debug(f"Sudachi tokenization error in sentence: {e}")

        # Supplementary matching: check for multi-word or compound predicates in sentence
        def _stem_matches(p: str, s: str) -> bool:
            if p in s:
                return True
            if p.endswith("になる"):
                stem = p[:-3]
                return bool(re.search(rf"{re.escape(stem)}(?:になり|になった|になる|になっ)", s))
            if p.endswith("にする"):
                stem = p[:-3]
                return bool(re.search(rf"{re.escape(stem)}(?:にし|にした|にする)", s))
            if p.endswith("される"):
                stem = p[:-3]
                return bool(re.search(rf"{re.escape(stem)}(?:され|した|する)", s))
            if p.endswith("する"):
                stem = p[:-2]
                return bool(re.search(rf"{re.escape(stem)}(?:し|する|され)", s))
            if p.endswith("く"):
                stem = p[:-1]
                return bool(re.search(rf"{re.escape(stem)}(?:い|か|く)", s))
            if p.endswith("す"):
                stem = p[:-1]
                return bool(re.search(rf"{re.escape(stem)}(?:し|す|され)", s))
            if p.endswith("る"):
                stem = p[:-1]
                return bool(re.search(rf"{re.escape(stem)}(?:た|て|る|れ)", s))
            return False

        for pred in RESOLVED_PREDICATES:
            if _stem_matches(pred, sentence):
                extracted_predicates.append(pred)
        for pred in PROGRESSED_PREDICATES:
            if _stem_matches(pred, sentence):
                extracted_predicates.append(pred)
        for pred in MENTION_ONLY_PREDICATES:
            if _stem_matches(pred, sentence):
                extracted_predicates.append(pred)

        results: List[Tuple[str, str]] = []
        for pred in extracted_predicates:
            if pred in RESOLVED_PREDICATES:
                results.append((pred, "resolved"))
            elif pred in PROGRESSED_PREDICATES:
                results.append((pred, "progressed"))
            elif pred in MENTION_ONLY_PREDICATES:
                results.append((pred, "mention_only"))
            else:
                results.append((pred, "unknown"))

        return results

    def analyze_foreshadowing(
        self,
        foreshadowing_id: int,
        keywords: List[str],
        text: str,
    ) -> PredicateAnalysisResult:
        """
        Analyze all occurrences of the foreshadowing keywords in text and evaluate predicates.

        Args:
            foreshadowing_id: ID of the foreshadowing item
            keywords: List of search keywords for this item
            text: Novel text to analyze

        Returns:
            PredicateAnalysisResult
        """
        matches: List[PredicateMatch] = []
        sentences = self.split_sentences(text)

        for sentence in sentences:
            for kw in keywords:
                if kw in sentence:
                    preds = self.analyze_sentence(sentence, kw)
                    for pred_str, pred_type in preds:
                        matches.append(
                            PredicateMatch(
                                keyword=kw,
                                predicate=pred_str,
                                predicate_type=pred_type,  # type: ignore
                                sentence=sentence,
                                confidence_score=0.9 if self._tokenizer else (0.85 if pred_type == "resolved" else 0.7),
                            )
                        )

        # Determine highest action
        has_resolved = any(m.predicate_type == "resolved" for m in matches)
        has_progressed = any(m.predicate_type == "progressed" for m in matches)
        has_mention_only = any(m.predicate_type == "mention_only" for m in matches)

        if has_resolved:
            highest_action = "resolved"
            syntax_score = 25
        elif has_progressed:
            highest_action = "progressed"
            syntax_score = 15
        elif has_mention_only or matches:
            highest_action = "mention_only"
            syntax_score = 5
        else:
            highest_action = "none"
            syntax_score = 0

        return PredicateAnalysisResult(
            foreshadowing_id=foreshadowing_id,
            matches=matches,
            highest_action=highest_action,
            syntax_score=syntax_score,
        )
