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
from src.models.foreshadowing_status import ForeshadowingStatus, ForeshadowingScope
from src.models.writing_metadata import WritingMetadata
from src.services.foreshadowing.ensemble_judge import EnsembleJudge
from src.services.foreshadowing.rescheduler import ForeshadowingRescheduler
from src.services.nlp.foreshadowing_predicate_analyzer import ForeshadowingPredicateAnalyzer

logger = logging.getLogger(__name__)


class ForeshadowingService:
    """伏線の回収検出・ステータス更新を一括で行うサービス。

    章の執筆完了後に呼び出され、本文中に回収が検出された伏線を
    自動的にDBで resolved に更新する。
    """

    def __init__(
        self,
        repo: DbForeshadowingRepository,
        predicate_analyzer: Optional[ForeshadowingPredicateAnalyzer] = None,
    ):
        self.repo = repo
        self.predicate_analyzer = predicate_analyzer or ForeshadowingPredicateAnalyzer()

    async def check_and_resolve(
        self,
        book_id: int,
        episode_num: int,
        draft_text: str,
        writing_metadata: Optional[WritingMetadata] = None,
        contract_ids: Optional[list[int]] = None,
    ) -> list[str]:
        """本文および共連れメタデータをアンサンブル解析し、回収された伏線を自動更新する。

        事後LLM呼び出し回数: 0回

        Args:
            book_id: 作品ID
            episode_num: 現在の話数
            draft_text: 生成された本文テキスト
            writing_metadata: 執筆時に共連れ出力されたメタデータ（任意）
            contract_ids: ビートシートで契約された伏線IDリスト（任意）

        Returns:
            回収された伏線タイトルのリスト
        """
        unresolved = await self.repo.get_unresolved(book_id)
        if not unresolved:
            return []

        resolved_titles: list[str] = []

        for f in unresolved:
            f_id = getattr(f, "id", None)
            if f_id is None:
                continue

            target_ep = getattr(f, "target_episode", None)
            is_contracted = bool(
                (contract_ids and f_id in contract_ids)
                or (target_ep == episode_num)
                or (target_ep is None and contract_ids is None)
            )

            # Metadata report matching
            meta_report = None
            if writing_metadata and writing_metadata.foreshadowings:
                meta_report = next(
                    (r for r in writing_metadata.foreshadowings if r.foreshadowing_id == f_id),
                    None,
                )

            # Syntactic predicate analysis
            keywords = [f.title]
            if hasattr(f, "keywords") and f.keywords:
                keywords.extend(f.keywords)
            keywords = list(dict.fromkeys(keywords))

            syntax_analysis = self.predicate_analyzer.analyze_foreshadowing(
                foreshadowing_id=f_id,
                keywords=keywords,
                text=draft_text,
            )

            # Ensemble voting
            judgment = EnsembleJudge.evaluate(
                foreshadowing_id=f_id,
                is_contracted=is_contracted,
                metadata_report=meta_report,
                syntax_analysis=syntax_analysis,
            )

            if judgment.status == "RESOLVED":
                success = await self.repo.resolve(f_id, episode_num)
                if success:
                    resolved_titles.append(f.title)
                    logger.info(
                        f"伏線「{f.title}」を RESOLVED に更新 ({judgment.rationale})"
                    )
            elif judgment.status == "PROGRESSED":
                await self.repo.progress(f_id)
                logger.info(
                    f"伏線「{f.title}」を PROGRESSED に更新 ({judgment.rationale})"
                )

            # Reschedule if target episode passed or contracted but not resolved
            if judgment.should_reschedule:
                await ForeshadowingRescheduler.reschedule_foreshadowing(
                    foreshadowing_id=f_id,
                    current_episode=episode_num,
                    repo=self.repo,
                )

        return resolved_titles

    async def get_writing_context(self, book_id: int, episode_num: int) -> dict[str, list[dict[str, Any]]]:
        """話数進捗に応じた未回収伏線をプロンプト注入用に分離して取得する。

        Args:
            book_id: 作品ID
            episode_num: 現在の話数

        Returns:
            dict with keys 'short_term' and 'long_term', each being a list of foreshowing dicts.
        """
        # 短期伏線（scope=short_term）を取得
        short_term = await self.repo.get_unresolved_by_scope(book_id, ForeshadowingScope.SHORT_TERM)
        # 長期伏線（scope=long_term）を取得
        long_term = await self.repo.get_unresolved_by_scope(book_id, ForeshadowingScope.LONG_TERM)
        return {
            "short_term": [
                {
                    "id": f.id,
                    "title": f.title,
                    "description": f.description,
                    "planted_episode": f.planted_episode,
                    "target_episode": f.target_episode,
                    "status": f.status,
                }
                for f in short_term
            ],
            "long_term": [
                {
                    "id": f.id,
                    "title": f.title,
                    "description": f.description,
                    "planted_episode": f.planted_episode,
                    "target_episode": f.target_episode,
                    "status": f.status,
                }
                for f in long_term
            ],
        }

    async def get_contract_foreshadowings(
        self,
        book_id: int,
        episode_num: int,
        target_ids: Optional[list[int]] = None,
    ) -> list[dict[str, Any]]:
        """ビートシート契約に基づき、本話で回収すべき伏線の一覧を取得する。

        Args:
            book_id: 作品ID
            episode_num: 現在の話数
            target_ids: ビートシートで明示された回収対象伏線IDリスト（省略時は目標話数一致伏線）

        Returns:
            プロンプト注入用の伏線辞書リスト
        """
        if target_ids:
            records = await self.repo.get_by_ids(target_ids)
            # 未回収のものだけに限定
            active_records = [r for r in records if r.book_id == book_id and getattr(r, "status", "") in ForeshadowingStatus.active_statuses()]
        else:
            # target_idsが明示されていない場合は目標話数が本話のものを検索
            unresolved = await self.repo.get_unresolved(book_id)
            active_records = [r for r in unresolved if getattr(r, "target_episode", None) == episode_num]

        return [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "planted_episode": f.planted_episode,
                "target_episode": f.target_episode,
                "scope": getattr(f, "scope", "short_term"),
            }
            for f in active_records
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