"""
シリーズ完結処理モジュール
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.easy_mode.models import EpisodeResult


class SeriesFinalizer:
    """シリーズ完結処理・メタデータ生成"""

    def __init__(self, preset: Dict[str, Any]):
        self.preset = preset

    async def finalize(
        self, bible: Dict, plot_outline: List, episodes: List[EpisodeResult]
    ) -> Dict[str, Any]:
        """シリーズ完結処理・メタデータ生成"""
        total_words = sum(ep.word_count for ep in episodes)
        avg_score = sum(ep.audit_score for ep in episodes) / len(episodes) if episodes else 0

        # タイトル生成
        titles = self.preset.get("titles", {})
        title = titles.get("title_templates", ["無題"])[0]

        # あらすじ生成
        marketing = self.preset.get("marketing", {})
        synopsis = marketing.get("synopsis_structure", {})

        return {
            "title": title,
            "concept": marketing.get("synopsis_structure", {}).get("hook", ""),
            "total_words": total_words,
            "average_audit_score": round(avg_score, 1),
            "episodes_completed": len(episodes),
            "synopsis": synopsis,
            "tags": marketing.get("tags", [])[:10],
            "catchphrase": marketing.get("catchphrase_templates", [""])[0],
        }
