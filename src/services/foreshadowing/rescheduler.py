"""Foreshadowing rescheduler for postponing unfulfilled foreshadowing resolution."""

import logging
from typing import Optional

from src.config.commercial_beat_sheet import COMMERCIAL_40EP_BEATS, get_beat_for_episode
from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository

logger = logging.getLogger(__name__)


class ForeshadowingRescheduler:
    """Automatically reschedules unresolved foreshadowings to subsequent suitable beats."""

    @classmethod
    def find_next_suitable_episode(cls, current_episode: int, max_episode: int = 40) -> int:
        """
        Find the next episode suitable for foreshadowing resolution based on beat sheet directives.

        Args:
            current_episode: The current episode number
            max_episode: Total planned episodes

        Returns:
            Next target episode number
        """
        for ep in range(current_episode + 1, max_episode + 1):
            beat = get_beat_for_episode(ep)
            if beat:
                # Check if beat directive mentions resolution/recovery
                fs_dir = beat.get("foreshadowing_directive", "") if isinstance(beat, dict) else getattr(beat, "foreshadowing_directive", "")
                if "回収" in str(fs_dir):
                    return ep

        # Fallback: postpone by 2 episodes or clamp to max_episode
        return min(current_episode + 2, max_episode)

    @classmethod
    async def reschedule_foreshadowing(
        cls,
        foreshadowing_id: int,
        current_episode: int,
        repo: DbForeshadowingRepository,
        max_episode: int = 40,
    ) -> Optional[int]:
        """
        Reschedule a foreshadowing item to a future episode in the repository.

        Args:
            foreshadowing_id: ID of the foreshadowing
            current_episode: Current episode
            repo: Foreshadowing repository
            max_episode: Maximum episode bound

        Returns:
            New target episode, or None if failed
        """
        new_target = cls.find_next_suitable_episode(current_episode, max_episode)
        try:
            # Update target episode in DB
            if hasattr(repo, "update_target_episode"):
                await repo.update_target_episode(foreshadowing_id, new_target)
            logger.info(
                f"Rescheduled foreshadowing id={foreshadowing_id} from ep={current_episode} to target_ep={new_target}"
            )
            return new_target
        except Exception as e:
            logger.warning(f"Failed to reschedule foreshadowing id={foreshadowing_id}: {e}")
            return None
