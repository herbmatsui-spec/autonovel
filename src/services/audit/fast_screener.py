"""
High-speed screener for early exit in audit pipeline.
Uses a lightweight LLM to quickly determine if text passes basic quality thresholds.
"""

from typing import Tuple

class FastScreener:
    """
    A simple screener that uses a lightweight LLM (or mock) to screen text.
    In production, this would call an external API like Gemini 2.0 Flash.
    """

    def __init__(self, threshold: float = 80.0):
        """
        Initialize the screener with a quality threshold.
        Args:
            threshold: Score above which the text is considered passing (0-100 scale).
        """
        self.threshold = threshold

    async def screen(self, text: str) -> Tuple[float, bool]:
        """
        Screen the text and return a score and whether it passes the threshold.
        Args:
            text: The text to screen.
        Returns:
            A tuple (score, passed) where score is a float (0-100) and passed is bool.
        """
        # TODO: Replace with actual LLM call
        # For now, we return a mock score based on text length (just for demonstration)
        # This is a placeholder and should be replaced with real screening logic.
        score = min(100.0, len(text) * 0.1)  # Mock score: 0.1 per character, max 100
        passed = score >= self.threshold
        return score, passed
