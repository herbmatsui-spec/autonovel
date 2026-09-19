"""Syntax refiner for purple prose detox.

Provides sentence-level refinement to simplify excessive descriptions
while preserving meaning and improving prose quality.
"""

from __future__ import annotations

import re
from typing import Tuple, List, Dict


class SyntaxRefiner:
    """Refines sentence syntax to reduce purple prose elements.
    
    Applies transformations:
    1. Collapse violent/aggressive verbs to stronger single verbs
    2. Simplify metaphorical constructions
    3. Convert to more direct, active voice
    4. Apply 体言止め (noun-ending) for impact where appropriate
    """
    
    # Mapping of aggressive verb phrases to simpler, stronger alternatives
    AGGRESSIVE_VERB_MAP: Dict[str, str] = {
        "歯を食いしば": "耐えた",
        "舌打ちした": "眉をひそめた",
        "拳を握りしめた": "こらえた",
        "胃を痛めた": "ぐっときた",
        "血の気が引いた": "身がすくんだ",
        "激痛が脳を焼いた": "麻痺した",
        "視線が氷のように": "凛とした",
        "奥歯を軋ませた": "ぐっと歯を食いしばった",
    }
    
    # Metaphor simplification patterns
    METAPHOR_SIMPLIFICATIONS: List[Tuple[re.Pattern, str]] = [
        # まるでXのように → Xのような (keep the simile but make it cleaner)
        (re.compile(r"まるで([^、。]{1,20})よう"), r"\1のような"),
        # XのようにY → Y felt like X (restructure)
        (re.compile(r"([^、。]{1,20})ように([^、。]{1,20})"), r"\2は\1のように感じた"),
        # まるでXだ → Xだった (direct statement)
        (re.compile(r"まるで([^、。]{1,20})だ"), r"\1だった"),
    ]
    
    # Patterns for 体言止め conversion (where appropriate)
    NOUN_ENDING_PATTERNS: List[Tuple[re.Pattern, str]] = [
        # ...していた → ...た (simple past)
        (re.compile(r"(.+?)していた([。！？\n]|$)"), r"\1た\2"),
        # ...していたが → ...たが (contrastive)
        (re.compile(r"(.+?)していたが"), r"\1たが"),
        # ...している → ...ています (polite continuous) -> ...た (simple past for impact)
        (re.compile(r"(.+?)している([。！？\n]|$)"), r"\1た\2"),
    ]
    
    # Filler words and hedge words to remove
    FILLER_PATTERNS: List[re.Pattern] = [
        re.compile(r"\s+(かな|かなぁ|でしょう|でしょうか|でしょうね)\s*"),
        re.compile(r"\s+(たぶん|おそらく|もしかしたら)\s*"),
        re.compile(r"\s+(まるで|ように|かのよう)\s+(?=[^、。])"),  # When followed by more text
    ]

    def __init__(self) -> None:
        """Initialize the syntax refiner."""
        pass

    def refine_paragraph(
        self, 
        paragraph: str, 
        aggressive_used: int = 0, 
        metaphor_used: int = 0
    ) -> Tuple[str, int, int]:
        """Refine a paragraph to reduce purple prose elements.
        
        Args:
            paragraph: Input paragraph to refine
            aggressive_used: Count of aggressive reactions already used in episode
            metaphor_used: Count of metaphors already used in episode
            
        Returns:
            Tuple of (refined_paragraph, updated_aggressive_used, updated_metaphor_used)
        """
        if not paragraph or not paragraph.strip():
            return paragraph, aggressive_used, metaphor_used
        
        # Split into sentences while preserving delimiters
        sentences = self._split_sentences_keep_delimiters(paragraph)
        
        refined_sentences = []
        current_aggressive = aggressive_used
        current_metaphor = metaphor_used
        
        for sentence in sentences:
            if not sentence.strip():
                refined_sentences.append(sentence)
                continue
                
            refined_sentence, current_aggressive, current_metaphor = self._refine_sentence(
                sentence, current_aggressive, current_metaphor
            )
            refined_sentences.append(refined_sentence)
        
        return "".join(refined_sentences), current_aggressive, current_metaphor
    
    def _refine_sentence(
        self, 
        sentence: str, 
        aggressive_used: int, 
        metaphor_used: int
    ) -> Tuple[str, int, int]:
        """Refine a single sentence.
        
        Args:
            sentence: Input sentence to refine
            aggressive_used: Count of aggressive reactions already used
            metaphor_used: Count of metaphors already used
            
        Returns:
            Tuple of (refined_sentence, updated_aggressive_used, updated_metaphor_used)
        """
        # Work on a copy
        refined = sentence
        
        # 1. Handle aggressive verb replacements (with limits)
        for agg_pattern, replacement in self.AGGRESSIVE_VERB_MAP.items():
            if agg_pattern in refined:
                # Count occurrences
                occurrences = len(re.findall(re.escape(agg_pattern), refined))
                
                # If we're under the limit (2 per episode), we can keep some
                # But for detox, we want to replace excess with simpler verbs
                if aggressive_used >= 2:
                    # Over limit: replace all occurrences
                    refined = refined.replace(agg_pattern, replacement)
                    aggressive_used += occurrences
                else:
                    # Under limit: we can keep one, replace the rest
                    # Keep the first occurrence, replace subsequent ones
                    parts = re.split(f"({re.escape(agg_pattern)})", refined)
                    new_parts = []
                    first_kept = False
                    
                    for part in parts:
                        if part == agg_pattern:
                            if not first_kept and aggressive_used < 2:
                                # Keep first one (or up to limit)
                                new_parts.append(part)
                                aggressive_used += 1
                                first_kept = True
                            else:
                                # Replace excess occurrences
                                new_parts.append(replacement)
                                aggressive_used += 1
                        else:
                            new_parts.append(part)
                    
                    refined = "".join(new_parts)
        
        # 2. Simplify metaphors (with limits)
        for pattern, replacement in self.METAPHOR_SIMPLIFICATIONS:
            matches = list(pattern.finditer(refined))
            if matches:
                # Process from end to start to maintain indices
                offsets = [(m.start(), m.end()) for m in matches]
                
                for start, end in reversed(offsets):
                    matched_text = refined[start:end]
                    # Count this as a metaphor usage
                    if metaphor_used >= 3:
                        # Over limit: simplify/remove
                        refined = refined[:start] + replacement + refined[end:]
                        metaphor_used += 1
                    else:
                        # Under limit: apply mild simplification
                        simplified = self._apply_metaphor_simplification(matched_text)
                        if simplified != matched_text:
                            refined = refined[:start] + simplified + refined[end:]
                            metaphor_used += 1
        
        # 3. Apply noun-ending (体言止め) for impact where appropriate
        # But only if we're not over-using metaphors (to avoid making it too choppy)
        if metaphor_used < 2:  # Only apply noun-ending if metaphors are under control
            for pattern, replacement in self.NOUN_ENDING_PATTERNS:
                refined = pattern.sub(replacement, refined)
        
        # 4. Remove filler/hedge words
        for pattern in self.FILLER_PATTERNS:
            refined = pattern.sub(" ", refined)
        
        # Clean up extra spaces
        refined = re.sub(r"\s+", " ", refined)
        refined = refined.strip()
        
        return refined, aggressive_used, metaphor_used
    
    def _apply_metaphor_simplification(self, metaphor_text: str) -> str:
        """Apply simplification to a metaphorical phrase.
        
        Args:
            metaphor_text: The metaphorical text to simplify
            
        Returns:
            Simplified version
        """
        # Try each simplification pattern
        for pattern, replacement in self.METAPHOR_SIMPLIFICATIONS:
            match = pattern.search(metaphor_text)
            if match:
                # Apply the replacement
                return pattern.sub(replacement, metaphor_text, count=1)
        
        # If no specific pattern matched, try to extract the core comparison
        # "まるでXのようにY" -> "Y felt like X"
        if "まるで" in metaphor_text and "よう" in metaphor_text:
            # Extract X and Y from 「まるでXようY」 or similar
            match = re.search(r"まるで(.+?)よう(.+)", metaphor_text)
            if match:
                x_part = match.group(1).strip()
                y_part = match.group(2).strip()
                if y_part:
                    return f"{y_part}は{x_part}のように感じた"
                else:
                    return f"{x_part}だった"
        
        # "XのようにY" -> "Y felt like X"
        if "ように" in metaphor_text:
            match = re.search(r"(.+?)ように(.+)", metaphor_text)
            if match:
                x_part = match.group(1).strip()
                y_part = match.group(2).strip()
                if y_part and x_part:
                    return f"{y_part}は{x_part}のように感じた"
        
        # If we can't simplify meaningfully, return a basic version
        return metaphor_text.replace("まるで", "").replace("ように", "").replace("かのよう", "")
    
    def _split_sentences_keep_delimiters(self, text: str) -> List[str]:
        """Split text into sentences while keeping delimiters.
        
        Args:
            text: Input text to split
            
        Returns:
            List of sentence fragments including delimiters
        """
        # Split by Japanese sentence endings and punctuation
        # Keep the delimiters with the preceding text
        sentence_endings = r"[。！？\n]"
        parts = re.split(f"({sentence_endings})", text)
        
        sentences = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and re.match(sentence_endings, parts[i + 1]):
                # Combine text with its delimiter
                sentences.append(parts[i] + parts[i + 1])
                i += 2
            else:
                # Just text (no delimiter)
                if parts[i].strip():  # Only add non-empty parts
                    sentences.append(parts[i])
                i += 1
                
        return [s for s in sentences if s]  # Filter out empty strings