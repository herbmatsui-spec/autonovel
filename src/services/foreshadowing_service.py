"""伏線回収ステータス自動更新サービス (v5.0 Relational Memory)

執筆完了時に本文を解析し、回収された伏線を自動的に
ForeshadowingStatus.RESOLVED に更新する。
"""
from __future__ import annotations

import logging
from typing import Any

from src.domain.schemas.foreshadowing import (
    ForeshadowingGraphResponse,
    GraphEdgeSchema,
    GraphNodeSchema,
)
from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository
from src.models.foreshadowing_status import ForeshadowingStatus
from src.services.foreshadowing_parser import detect_foreshadowing_mentions

logger = logging.getLogger(__name__)


class ForeshadowingService:
    """伏線の回収検出・ステータス更新を一括で行うサービス。

    章の執筆完了後に呼び出され、本文中に回収が検出された伏線を
    自動的にDBで resolved に更新する。
    """

    def __init__(self, repo: DbForeshadowingRepository):
        self.repo = repo

    async def check_and_resolve(
        self,
        book_id: int,
        episode_num: int,
        draft_text: str,
    ) -> list[str]:
        """本文を解析し、回収された伏線を自動更新する。

        Args:
            book_id: 作品ID
            episode_num: 現在の話数
            draft_text: 生成された本文テキスト

        Returns:
            回収された伏線タイトルのリスト
        """
        # 未回収伏線を取得
        unresolved = await self.repo.get_unresolved(book_id)
        if not unresolved:
            return []

        # 本文中の伏線言及を検出
        mentions = detect_foreshadowing_mentions(draft_text, unresolved)

        resolved_titles: list[str] = []

        for mention in mentions:
            # 回収候補と判定された伏線のみ自動回収
            if not mention.is_resolution_candidate:
                continue

            # 回収対象の伏線を検索
            foreshadowing = self._find_by_id(unresolved, mention.foreshadowing_id)
            if foreshadowing is None:
                continue

            # 回収目標話数を超えているか、目標未設定の場合は回収
            target_ep = getattr(foreshadowing, "target_episode", None)
            if target_ep is not None and episode_num < target_ep:
                # まだ目標話数に到達していないので進展扱い
                await self.repo.progress(mention.foreshadowing_id)
                logger.info(
                    f"伏線「{mention.title}」を PROGRESSED に更新 "
                    f"(book_id={book_id}, ep={episode_num}, target={target_ep})"
                )
                continue

            # 回収処理
            success = await self.repo.resolve(mention.foreshadowing_id, episode_num)
            if success:
                resolved_titles.append(mention.title)
                logger.info(
                    f"伏線「{mention.title}」を RESOLVED に更新 "
                    f"(book_id={book_id}, ep={episode_num})"
                )

        return resolved_titles

    async def get_writing_context(self, book_id: int) -> list[dict[str, Any]]:
        """未回収伏線をプロンプト注入用の辞書リストとして取得する。

        Returns:
            [{"id": int, "title": str, "description": str, "planted_episode": int, ...}, ...]
        """
        unresolved = await self.repo.get_unresolved(book_id)
        return [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "planted_episode": f.planted_episode,
                "target_episode": f.target_episode,
                "status": f.status,
            }
            for f in unresolved
        ]

    async def get_overdue_warnings(self, book_id: int, current_episode: int) -> list[str]:
        """回収期限を超過した伏線の警告メッセージを返す"""
        overdue = await self.repo.get_overdue(book_id, current_episode)
        return [
            f"⚠ 伏線「{f.title}」が回収期限（第{f.target_episode}話）を"
            f"{current_episode - f.target_episode}話超過しています"
            for f in overdue
        ]

    @staticmethod
    def _find_by_id(foreshadowings: list, foreshadowing_id: int) -> Any:
        """IDで伏線を検索"""
        for f in foreshadowings:
            f_id = f.get("id") if isinstance(f, dict) else getattr(f, "id", None)
            if f_id == foreshadowing_id:
                return f
        return None

    async def get_foreshadowing_graph(self, book_id: int) -> ForeshadowingGraphResponse:
        """作品IDに紐づく伏線・キャラからForce-Graph向けのノード・エッジを生成する。

        Args:
            book_id: 作品ID

        Returns:
            ForeshadowingGraphResponse: ノードとエッジを含むグラフデータ
        """
        # 未回収・回収済み全ての伏線を取得
        all_foreshadowings = await self.repo.get_by_book_id(book_id)

        nodes: list[GraphNodeSchema] = []
        edges: list[GraphEdgeSchema] = []
        node_ids: set[str] = set()

        # 伏線ノード作成
        for f in all_foreshadowings:
            node_id = f"foreshadowing_{f.id}"
            if node_id in node_ids:
                continue
            node_ids.add(node_id)
            nodes.append(
                GraphNodeSchema(
                    id=node_id,
                    label="Foreshadowing",
                    properties={
                        "title": f.title,
                        "description": f.description,
                        "planted_episode": f.planted_episode,
                        "target_episode": f.target_episode,
                        "resolved_episode": f.resolved_episode,
                        "status": f.status,
                    },
                )
            )

        # キャラクター関連のノード・エッジは別途CharacterRepositoryから取得想定
        # ここでは伏線同士の関連（PLANTED_IN, RESOLVED_BY）をエッジとして構築
        for f in all_foreshadowings:
            source_id = f"foreshadowing_{f.id}"

            # 設置エピソードへのエッジ（概念的なノードとして扱う）
            ep_node_id = f"episode_{f.planted_episode}"
            if ep_node_id not in node_ids:
                node_ids.add(ep_node_id)
                nodes.append(
                    GraphNodeSchema(
                        id=ep_node_id,
                        label="Episode",
                        properties={"episode_number": f.planted_episode},
                    )
                )
            edges.append(
                GraphEdgeSchema(
                    source=source_id,
                    target=ep_node_id,
                    type="PLANTED_IN",
                    properties={},
                )
            )

            # 回収済みの場合、回収エピソードへのエッジ
            if f.resolved_episode is not None:
                resolved_ep_id = f"episode_{f.resolved_episode}"
                if resolved_ep_id not in node_ids:
                    node_ids.add(resolved_ep_id)
                    nodes.append(
                        GraphNodeSchema(
                            id=resolved_ep_id,
                            label="Episode",
                            properties={"episode_number": f.resolved_episode},
                        )
                    )
                edges.append(
                    GraphEdgeSchema(
                        source=source_id,
                        target=resolved_ep_id,
                        type="RESOLVED_BY",
                        properties={},
                    )
                )

            # 目標話数がある場合の関連エッジ
            if f.target_episode is not None:
                target_ep_id = f"episode_{f.target_episode}"
                if target_ep_id not in node_ids:
                    node_ids.add(target_ep_id)
                    nodes.append(
                        GraphNodeSchema(
                            id=target_ep_id,
                            label="Episode",
                            properties={"episode_number": f.target_episode, "is_target": True},
                        )
                    )
                edges.append(
                    GraphEdgeSchema(
                        source=source_id,
                        target=target_ep_id,
                        type="RELATED_TO",
                        properties={"relation": "target_episode"},
                    )
                )

        return ForeshadowingGraphResponse(
            graph_name=f"book_{book_id}_foreshadowing",
            nodes=nodes,
            edges=edges,
        )
