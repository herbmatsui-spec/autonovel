"""Purple Prose Detox Filter - Stream-based content filter for excessive descriptions.

Implements density limiting for dramatic physical reactions and metaphors
to prevent overuse of purple prose in generated text.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Tuple, Pattern, Match


class PurpleProseFilter:
    """Stream-based filter that limits density of purple prose elements.
    
    Tracks counts per episode and applies limits:
    - Aggressive physical reactions (teeth grinding, tongue clicking, etc.): max 2 per episode
    - Metaphorical expressions (ように, まるで, etc.): max 3 per 1000 characters
    """

    # Patterns for aggressive physical reactions
    AGGRESSIVE_PATTERNS: List[Tuple[Pattern[str], str]] = [
        (re.compile(r"歯を?食いしば\w*"), "歯を食いしばった"),
        (re.compile(r"舌打ち\w*"), "舌打ちした"),
        (re.compile(r"拳を握りしめ\w*"), "拳を握った"),
        (re.compile(r"胃を?痛め\w*"), "胃が痛んだ"),
        (re.compile(r"血の?気が?引\w*"), "血の気が引いた"),
        (re.compile(r"激痛が?脳を?焼\w*"), "激痛が走った"),
        (re.compile(r"視線が?氷の?よう\w*"), "視線を向けた"),
        (re.compile(r"奥歯を?軋ませ\w*"), "奥歯が軋んだ"),
    ]

    # Patterns for metaphorical expressions
    METAPHOR_PATTERNS: List[Tuple[Pattern[str], str]] = [
        (re.compile(r"まるで[^、。]{1,30}よう"), ""),  # Remove metaphor entirely
        (re.compile(r"[^、。]{1,30}のように[^、。]{1,30}"), ""),  # Remove simile
        (re.compile(r"[^、。]{1,30}かのよう[^、。]{1,30}"), ""),  # Remove comparative
    ]

    def __init__(
        self,
        max_aggressive_per_episode: int = 2,
        max_metaphor_per_1k_chars: int = 3,
    ) -> None:
        """Initialize the purple prose filter.
        
        Args:
            max_aggressive_per_episode: Maximum allowed aggressive reactions per episode
            max_metaphor_per_1k_chars: Maximum allowed metaphors per 1000 characters
        """
        self.max_aggressive_per_episode = max_aggressive_per_episode
        self.max_metaphor_per_1k_chars = max_metaphor_per_1k_chars
        
        # Reset counters for new episode
        self.reset()
        
        # Pre-compile all patterns for efficiency
        self._aggressive_regexes: List[Tuple[Pattern[str], str]] = [
            (pattern, replacement) for pattern, replacement in self.AGGRESSIVE_PATTERNS
        ]
        self._metaphor_regexes: List[Tuple[Pattern[str], str]] = [
            (pattern, replacement) for pattern, replacement in self.METAPHOR_PATTERNS
        ]

    def reset(self) -> None:
        """Reset counters for a new episode."""
        self._aggressive_count: int = 0
        self._metaphor_count: int = 0
        self._character_count: int = 0

    def process(self, text: str) -> str:
        """Process text stream and apply purple prose limits.
        
        Args:
            text: Input text chunk to process
            
        Returns:
            Filtered text with excessive purple prose elements limited/replaced
        """
        if not text:
            return text
            
        # Update character count for metaphor density calculation
        self._character_count += len(text)
        
        # Calculate current metaphor budget based on characters processed
        metaphor_budget = max(
            0, 
            self.max_metaphor_per_1k_chars - 
            (self._metaphor_count * 1000 // max(self._character_count, 1))
        )
        
        # Process aggressive patterns first
        processed_text = self._apply_pattern_limits(
            text, 
            self._aggressive_regexes,
            self._aggressive_count,
            self.max_aggressive_per_episode,
            lambda: setattr(self, '_aggressive_count', self._aggressive_count + 1),
            "aggressive"
        )
        
        # Process metaphor patterns with dynamic budget
        processed_text = self._apply_pattern_limits(
            processed_text,
            self._metaphor_regexes,
            self._metaphor_count,
            self._metaphor_count + metaphor_budget,  # Effective limit based on budget
            lambda: setattr(self, '_metaphor_count', self._metaphor_count + 1),
            "metaphor"
        )
        
        return processed_text

    def _apply_pattern_limits(
        self,
        text: str,
        pattern_replacements: List[Tuple[Pattern[str], str]],
        current_count: int,
        max_allowed: int,
        increment_counter: callable,
        pattern_type: str
    ) -> str:
        """Apply limits to a set of patterns in the text.
        
        Args:
            text: Input text
            pattern_replacements: List of (pattern, replacement) tuples
            current_count: Current count of matches found
            max_allowed: Maximum allowed matches
            increment_counter: Function to call when a match is within limits
            pattern_type: Type of pattern ("aggressive" or "metaphor") for debugging
            
        Returns:
            Text with pattern limits applied
        """
        if current_count >= max_allowed:
            # If we've already exceeded the limit, remove all matches
            result = text
            for pattern, replacement in pattern_replacements:
                result = pattern.sub(replacement, result)
            return result
        
        # We need to process matches one by one to apply limits correctly
        # Find all matches with their positions
        all_matches: List[Tuple[int, int, str, str]] = []  # (start, end, matched_text, replacement)
        
        for pattern, replacement in pattern_replacements:
            for match in pattern.finditer(text):
                all_matches.append((match.start(), match.end(), match.group(0), replacement))
        
        # Sort by position to process in order
        all_matches.sort(key=lambda x: x[0])
        
        # Apply limits: keep first N matches, replace/rest excess
        result_parts: List[str] = []
        last_end = 0
        matches_processed = 0
        
        for start, end, matched_text, replacement in all_matches:
            # Add text before this match
            result_parts.append(text[last_end:start])
            
            # Check if we're within limits
            if (current_count + matches_processed) < max_allowed:
                # Within limits: keep original or apply transformation
                if replacement:  # Non-empty replacement means transform
                    result_parts.append(replacement)
                else:  # Empty replacement means keep original (for metaphor patterns we might want to keep some)
                    # For metaphors, we might want to keep the core meaning but remove flowery language
                    # For now, if replacement is empty, we'll remove the metaphor entirely
                    pass  # Don't add anything (removes the match)
                matches_processed += 1
            else:
                # Exceeded limits: apply replacement (usually removal or simplification)
                if replacement:
                    result_parts.append(replacement)
                # If replacement is empty, we don't add anything (removes the match)
            
            last_end = end
        
        # Add remaining text after last match
        result_parts.append(text[last_end:])
        
        # Update counters
        if pattern_type == "aggressive":
            self._aggressive_count += matches_processed
        elif pattern_type == "metaphor":
            self._metaphor_count += matches_processed
            
        return "".join(result_parts)

    def get_stats(self) -> Dict[str, int]:
        """Get current filter statistics.
        
        Returns:
            Dictionary with counts for monitoring and debugging
        """
        return {
            "aggressive_count": self._aggressive_count,
            "metaphor_count": self._metaphor_count,
            "character_count": self._character_count,
            "aggressive_per_episode": self._aggressive_count,
            "metaphor_per_1k_chars": (
                self._metaphor_count * 1000 // max(self._character_count, 1)
            ) if self._character_count > 0 else 0
        }