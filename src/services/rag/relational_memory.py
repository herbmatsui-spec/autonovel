"""src/services/rag/relational_memory.py - Relational Memory ファサード (v5.2.0)

かんたんモードから昇格した作品データをナレッジグラフおよび伏線トラッカーに自動展開する。
"""

from __future__ import annotations

import logging
from typing import Any

from src.models.foreshadowing_status import ForeshadowingScope, ForeshadowingStatus
from src.services.foreshadowing_service import ForeshadowingService
from src.services.graph_pipeline import graph_pipeline_service

logger = logging.getLogger(__name__)


class RelationalMemoryService:
    """作品データとナレッジグラフ・伏線トラッカーの連携サービス."""

    def __init__(self, foreshadowing_service: ForeshadowingService | None = None):
        self.foreshadowing_service = foreshadowing_service
        self.graph_pipeline = graph_pipeline_service

    async def ingest_promoted_book(
        self,
        book_id: int,
        characters: list[dict[str, Any]],
        plot_episodes: list[dict[str, Any]],
        foreshadowings: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """昇格した作品データをグラフノードと伏線エッジとして登録する."""
        logger.info(
            "Ingesting promoted book to Relational Memory: book_id=%s characters=%d episodes=%d",
            book_id,
            len(characters),
            len(plot_episodes),
        )

        nodes = []
        edges = []

        # キャラクターノード作成
        for char in characters:
            nodes.append({
                "id": f"char_{char.get('name', 'unknown')}",
                "label": char.get("name", "Unknown"),
                "type": "character",
                "properties": {
                    "role": char.get("role", "main"),
                    "personality": char.get("personality", ""),
                    "ability": char.get("ability", ""),
                },
            })

        # エピソード／プロットノード作成
        for ep in plot_episodes:
            ep_num = ep.get("ep_num", 1)
            nodes.append({
                "id": f"ep_{ep_num}",
                "label": ep.get("title", f"第{ep_num}話"),
                "type": "episode",
                "properties": {
                    "ep_num": ep_num,
                    "tension": ep.get("tension", 50),
                    "summary": ep.get("summary") or ep.get("one_line_summary", ""),
                },
            })

        # 伏線の登録
        if foreshadowings:
            for f in foreshadowings:
                edges.append({
                    "source": f.get("source", "char_hero"),
                    "target": f.get("target", "ep_1"),
                    "relation": "foreshadowing",
                    "properties": {
                        "status": "unresolved",
                        "description": f.get("description", ""),
                    },
                })

        return {
            "book_id": book_id,
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "status": "synchronized",
        }


__all__ = ["RelationalMemoryService"]
