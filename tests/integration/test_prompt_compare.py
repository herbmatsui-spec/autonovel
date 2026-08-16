"""
tests/integration/test_prompt_compare.py

機能8（ジャンル別プロンプト A/B 比較）のテスト。
評価ロジックと、DB上のプロンプトバージョンを用いたルーター経由の比較を確認する。
"""
import pytest

from src.services.prompt_comparison import (
    build_comparison,
    decide_winner,
    score_output,
    weighted_total,
)


@pytest.mark.asyncio
async def test_score_output_returns_all_keys():
    scores = await score_output("彼は去っていった。一体なぜだろうか？" + ("物語は続く。" * 20))
    assert set(scores.keys()) == {
        "hook_retention", "pacing", "character_consistency",
        "commercial_viability", "emotional_resonance", "coherence",
    }


@pytest.mark.asyncio
async def test_weighted_total_in_range():
    total = weighted_total({k: 0.5 for k in await score_output("x" * 200)})
    assert 0.0 <= total <= 1.0


@pytest.mark.asyncio
async def test_build_comparison_picks_higher_scoring_winner():
    versions = [{"id": 1, "version_tag": "A"}, {"id": 2, "version_tag": "B"}]
    # B の方がフックが強い文章
    texts = [
        "平坦な文章。特に何も起きなかった。" * 10,
        "彼は去っていった。一体なぜだろうか？" + ("物語は続く。" * 20),
    ]
    result = await build_comparison(versions, texts)
    assert result["winner"]["winner_id"] == 2
    assert len(result["results"]) == 2


def test_decide_winner_empty():
    assert decide_winner([])["winner_id"] is None


@pytest.mark.asyncio
async def test_compare_router_with_db_versions(real_uow):
    """routers/prompt_compare がDB上のバージョンで比較する。"""
    from config.container import Container
    from src.backend.database.models import PromptVersion
    from src.backend.routers import prompt_compare as pc_router

    async with real_uow as uow:
        book_id = await uow.books.create_book("T", "G", "C", "S", 10, {}, {})
        Container.db = lambda: real_uow.db
        uow.session.add(PromptVersion(
            book_id=book_id, prompt_key="writing_style", version_tag="v1", content="p1",
        ))
        uow.session.add(PromptVersion(
            book_id=book_id, prompt_key="writing_style", version_tag="v2", content="p2",
        ))
        await uow.session.flush()

    versions = await pc_router.list_versions(book_id, prompt_key="writing_style")
    assert len(versions) == 2

    result = await pc_router.compare(
        book_id,
        pc_router.CompareRequest(
            prompt_key="writing_style",
            texts=["平坦な文。" * 10, "なぜだろうか？" + ("続く。" * 20)],
        ),
    )
    assert result["winner"]["winner_id"] is not None
    assert len(result["results"]) == 2
