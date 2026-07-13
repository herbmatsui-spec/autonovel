from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select

from src.backend.database.models import NarrativeMetric
from src.backend.database.repositories.base import BaseRepository


class NarrativeMetricRepository(BaseRepository[NarrativeMetric]):
    @property
    def model_class(self):
        return NarrativeMetric

    async def get_latest_narrative_metrics(
        self, book_id: int, branch_id: int, ep_num: int, scene_num: int
    ) -> Optional[Dict[str, Any]]:
        """
        指定されたシーンの直前の最新指標を取得する。
        1. 同一エピソードの前のシーン (scene_num - 1)
        2. 前のエピソードの最終シーン
        """
        # 1. 同一エピソードの前のシーンを検索
        if scene_num > 1:
            result = await self.session.execute(
                select(NarrativeMetric)
                .where(
                    NarrativeMetric.book_id == book_id,
                    NarrativeMetric.branch_id == branch_id,
                    NarrativeMetric.ep_num == ep_num,
                    NarrativeMetric.scene_num == scene_num - 1
                )
            )
            metrics = result.scalars().all()
            if metrics:
                return self._aggregate_metrics(metrics)

        # 2. 前のエピソードの最終シーンを検索
        if ep_num > 1:
            result = await self.session.execute(
                select(NarrativeMetric)
                .where(
                    NarrativeMetric.book_id == book_id,
                    NarrativeMetric.branch_id == branch_id,
                    NarrativeMetric.ep_num == ep_num - 1
                )
                .order_by(desc(NarrativeMetric.scene_num))
            )
            # 最新のシーン番号を特定
            latest_scene = result.scalar_one_or_none()
            if latest_scene:
                # そのシーンの全指標を再取得
                result = await self.session.execute(
                    select(NarrativeMetric)
                    .where(
                        NarrativeMetric.book_id == book_id,
                        NarrativeMetric.branch_id == branch_id,
                        NarrativeMetric.ep_num == ep_num - 1,
                        NarrativeMetric.scene_num == latest_scene.scene_num
                    )
                )
                metrics = result.scalars().all()
                return self._aggregate_metrics(metrics)

        return None

    async def save_scene_metrics(
        self, book_id: int, branch_id: int, ep_num: int, scene_num: int, scores: List[Dict[str, Any]], version: Optional[int] = None
    ) -> None:
        """
        シーンの指標を保存する。
        versionが指定されていない場合は、最新バージョンをインクリメントして保存する。
        """
        from sqlalchemy import func, select

        # 現在の最新バージョンを確認
        if version is None:
            result = await self.session.execute(
                select(func.max(NarrativeMetric.version))
                .where(
                    NarrativeMetric.book_id == book_id,
                    NarrativeMetric.branch_id == branch_id,
                    NarrativeMetric.ep_num == ep_num,
                    NarrativeMetric.scene_num == scene_num
                )
            )
            current_max = result.scalar()
            version = (current_max or 0) + 1

        # 指標の保存 (バージョン管理のため、削除せずに追加)
        for s in scores:
            metric = NarrativeMetric(
                book_id=book_id,
                branch_id=branch_id,
                ep_num=ep_num,
                scene_num=scene_num,
                metric_name=s["metric_name"],
                score=s["score"],
                reasoning=s.get("reasoning", ""),
                version=version
            )
            self.add(metric)

    async def delete_scene_metrics(self, book_id: int, branch_id: int, ep_num: int, scene_num: int) -> None:
        """
        指定されたシーンの全バージョンの指標を削除する。
        """
        from sqlalchemy import delete
        await self.session.execute(
            delete(NarrativeMetric).where(
                NarrativeMetric.book_id == book_id,
                NarrativeMetric.branch_id == branch_id,
                NarrativeMetric.ep_num == ep_num,
                NarrativeMetric.scene_num == scene_num
            )
        )

    def _aggregate_metrics(self, metrics: List[NarrativeMetric]) -> Dict[str, int]:
        """
        複数のMetricレコードを {metric_name: score} 形式に変換する。
        """
        return {m.metric_name: m.score for m in metrics}

    async def get_trend_metrics(self, book_id: int, branch_id: int) -> List[Dict[str, Any]]:
        """
        ブランチ内の全シーンの最新指標を時系列で取得する。
        """
        from sqlalchemy import func

        # 各シーン・各指標の最大バージョンのみを抽出するサブクエリ
        subq = (
            select(
                NarrativeMetric.ep_num,
                NarrativeMetric.scene_num,
                NarrativeMetric.metric_name,
                func.max(NarrativeMetric.version).label("max_version")
            )
            .where(
                NarrativeMetric.book_id == book_id,
                NarrativeMetric.branch_id == branch_id
            )
            .group_by(
                NarrativeMetric.ep_num,
                NarrativeMetric.scene_num,
                NarrativeMetric.metric_name
            )
        ).subquery()

        # 最新バージョンに紐づくレコードを結合して取得
        stmt = (
            select(NarrativeMetric)
            .join(
                subq,
                (NarrativeMetric.ep_num == subq.c.ep_num) &
                (NarrativeMetric.scene_num == subq.c.scene_num) &
                (NarrativeMetric.metric_name == subq.c.metric_name) &
                (NarrativeMetric.version == subq.c.max_version)
            )
            .order_by(NarrativeMetric.ep_num, NarrativeMetric.scene_num)
        )

        result = await self.session.execute(stmt)
        metrics = result.scalars().all()

        # シーンごとに集約
        trend = {}
        for m in metrics:
            key = (m.ep_num, m.scene_num)
            if key not in trend:
                trend[key] = {"ep_num": m.ep_num, "scene_num": m.scene_num, "scores": {}}
            trend[key]["scores"][m.metric_name] = m.score

        return list(trend.values())
