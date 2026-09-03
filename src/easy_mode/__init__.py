"""
かんたんモード パッケージ
"""

from .spice_guard import SpiceElement, SpiceGuard, create_spice_guard


# Compatibility classes for deprecated src.easy_mode.pipeline
class EpisodeResult:
    def __init__(
        self,
        episode_num,
        title,
        content,
        word_count,
        audit_score,
        audit_passed,
        rewrite_count,
        spice_elements,
        metadata,
        needs_human_review=False,
    ):
        self.episode_num = episode_num
        self.title = title
        self.content = content
        self.word_count = word_count
        self.audit_score = audit_score
        self.audit_passed = audit_passed
        self.rewrite_count = rewrite_count
        self.spice_elements = spice_elements
        self.metadata = metadata
        self.needs_human_review = needs_human_review


class SeriesResult:
    def __init__(
        self,
        genre,
        title,
        concept,
        total_episodes,
        episodes,
        bible,
        plot_outline,
        metadata,
        created_at=None,
        status="completed",
    ):
        self.genre = genre
        self.title = title
        self.concept = concept
        self.total_episodes = total_episodes
        self.episodes = episodes
        self.bible = bible
        self.plot_outline = plot_outline
        self.metadata = metadata
        self.created_at = created_at
        self.status = status


__all__ = [
    "SpiceGuard",
    "SpiceElement",
    "create_spice_guard",
    "EpisodeResult",
    "SeriesResult",
]
