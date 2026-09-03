"""`SeriesResult` / `EpisodeResult` をシリアライズするユーティリティ。

Router 層・タスク層から利用し、本文の全文をログや JSON レスポンスに展開しないよう
要約フィールドへ変換する。
"""

from __future__ import annotations

from typing import Any

from src.easy_mode import EpisodeResult, SeriesResult

__all__ = ["series_to_dict", "episode_summary"]

CONTENT_SNIPPET_CHARS = 200


def episode_summary(ep: EpisodeResult) -> dict[str, Any]:
    """`EpisodeResult` をログ・レスポンス向け dict へ変換する。"""
    content = ep.content or ""
    return {
        "episode_num": ep.episode_num,
        "title": ep.title,
        "word_count": ep.word_count,
        "audit_score": ep.audit_score,
        "audit_passed": ep.audit_passed,
        "rewrite_count": ep.rewrite_count,
        "needs_human_review": ep.needs_human_review,
        "content_snippet": content[:CONTENT_SNIPPET_CHARS],
    }


def series_to_dict(series: SeriesResult) -> dict[str, Any]:
    """`SeriesResult` を dict へ変換する。

    - 本文は先頭 200 字に切り詰めて `content_snippet` として格納
    - エピソード数は `total_episodes` として再掲
    - メタデータはそのままコピー
    """
    return {
        "genre": series.genre,
        "title": series.title,
        "concept": series.concept,
        "total_episodes": series.total_episodes,
        "status": series.status,
        "created_at": series.created_at.isoformat() if series.created_at else None,
        "episodes": [episode_summary(ep) for ep in series.episodes],
        "bible": series.bible,
        "plot_outline": series.plot_outline,
        "metadata": series.metadata,
    }
