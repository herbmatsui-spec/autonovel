"""tests/unit/test_relational_memory.py - Relational Memory 連携テスト."""

from __future__ import annotations

import pytest
from src.services.rag.relational_memory import RelationalMemoryService


@pytest.mark.asyncio
async def test_ingest_promoted_book_to_relational_memory():
    service = RelationalMemoryService()

    characters = [
        {"name": "アレン", "role": "主人公", "personality": "不屈", "ability": "神速の剣"},
        {"name": "シリア", "role": "ヒロイン", "personality": "冷静", "ability": "氷結魔法"},
    ]
    episodes = [
        {"ep_num": 1, "title": "第1話 追放された少年", "tension": 40, "one_line_summary": "理不尽な追放劇"},
        {"ep_num": 2, "title": "第2話 覚醒の刻", "tension": 75, "one_line_summary": "真の力を開放"},
    ]
    foreshadowings = [
        {"source": "char_アレン", "target": "ep_2", "description": "左腕に宿る黒き刻印の謎"},
    ]

    result = await service.ingest_promoted_book(
        book_id=42,
        characters=characters,
        plot_episodes=episodes,
        foreshadowings=foreshadowings,
    )

    assert result["book_id"] == 42
    assert result["nodes_count"] == 4  # 2 characters + 2 episodes
    assert result["edges_count"] == 1  # 1 foreshadowing
    assert result["status"] == "synchronized"
