"""テスト用マルチメディアフィクスチャおよびダミーデータ生成器。"""

from __future__ import annotations

from typing import Any
from src.easy_mode import EpisodeResult, SeriesResult


def make_minimal_preset(genre: str) -> dict[str, Any]:
    """genre のみから preset を組み立てる (テスト用)。"""
    return {
        "genre": genre,
        "characters": {"archetypes": {}},
        "erotic": {},
    }


def make_minimal_episode(num: int = 1, title: str = "テスト話") -> EpisodeResult:
    """単体エピソードを組み立てるテストヘルパ。"""
    content = (
        f"第{num}話のテスト本文です。\n\n主人公は困難に立ち向かった。\n「行くぞ」と彼は言った。\n"
    )
    return EpisodeResult(
        episode_num=num,
        title=title,
        content=content,
        word_count=len(content),
        audit_score=80.0,
        audit_passed=True,
        rewrite_count=0,
        spice_elements=[],
        metadata={},
        needs_human_review=False,
    )


def make_minimal_series(
    genre: str = "ハイファンタジー (R15)",
    title: str = "テストシリーズ",
    episode_count: int = 1,
) -> SeriesResult:
    """テストから利用する最小 SeriesResult を生成する。"""
    eps = [make_minimal_episode(i + 1, f"第{i + 1}話") for i in range(episode_count)]
    return SeriesResult(
        genre=genre,
        title=title,
        concept="テストコンセプト",
        total_episodes=episode_count,
        episodes=eps,
        bible={},
        plot_outline=[],
        metadata={"prologue": f"{title} - 始まりの物語"},
    )
