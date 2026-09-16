"""
Scene tier evaluator for determining if a scene is a climax (Tier 3) or not.
"""

from typing import Any


class SceneTierEvaluator:
    """
    Evaluates whether a given scene (episode/chapter) is a climax based on
    plot tension, catharsis flags, and episode position.
    """

    def __init__(
        self,
        plot_service: Any | None = None,
    ):
        self.plot_service = plot_service

    async def is_climax(
        self, book_id: int, episode_number: int, total_episodes: int
    ) -> bool:
        """
        Determine if the given episode is a climax.

        Args:
            book_id: ID of the book/novel
            episode_number: The episode number (1-indexed)
            total_episodes: Total number of episodes in the book

        Returns:
            True if the episode is considered a climax (should use Tier 3 model)
        """
        # Get plot data for the book
        plot = await self.plot_service.get_plot_by_book_id(book_id)
        if not plot:
            # If no plot data, default to not climax
            return False

        # Get tension for this episode (assuming we have a method)
        tension = await self.plot_service.get_tension_for_episode(book_id, episode_number)
        # Check if there's a catharsis event in this episode
        is_catharsis = await self.plot_service.is_catharsis_episode(book_id, episode_number)

        # Condition 1: High tension (>= 80)
        if tension is not None and tension >= 80:
            return True

        # Condition 2: Catharsis event
        if is_catharsis:
            return True

        # Condition 3: First episode, middle episode, or last episode
        if episode_number == 1 or episode_number == total_episodes:
            return True
        # Middle episode: if total_episodes is odd, middle is (total_episodes//2)+1
        # We'll consider the middle episode as the one at index total_episodes//2 (1-indexed: total_episodes//2 + 1?)
        # For simplicity, we'll check if episode_number is approximately the middle.
        middle = total_episodes // 2 + 1  # 1-indexed middle
        if episode_number == middle:
            return True

        return False
