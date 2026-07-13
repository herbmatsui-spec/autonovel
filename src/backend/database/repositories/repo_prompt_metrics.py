"""
database/repo_prompt_metrics.py - プロンプト使用メトリクスのリポジトリ
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import delete, desc, select

from services.errors import retry_on_lock
from src.backend.database.models import PromptUsageLog
from src.backend.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PromptMetricsRepository(BaseRepository):
    """プロンプト使用メトリクスに関するDB操作をまとめたリポジトリ"""

    @retry_on_lock()
    async def save_metrics_snapshot(self, metrics: Dict[str, Dict[str, Any]]) -> None:
        """
        PromptRegistryのメトリクスをスナップショットとして保存
        
        Args:
            metrics: PromptRegistry.get_metrics()の返り値
        """
        for template_name, metric_data in metrics.items():
            log_entry = PromptUsageLog(
                template_name=template_name,
                hits=metric_data.get('hits', 0),
                total_time_ms=metric_data.get('total_time_ms', 0.0),
                avg_time_ms=metric_data.get('avg_time_ms', 0.0),
                last_accessed=metric_data.get('last_accessed', datetime.now()),
                error_count=metric_data.get('error_count', 0)
            )
            self.session.add(log_entry)

        # コミットは呼び出し側で行うか、UnitOfWorkで管理される

    @retry_on_lock()
    async def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        最近のメトリクススナップショットを取得
        
        Args:
            limit: 取得する最大レコード数
            
        Returns:
            メトリクスの辞書リスト
        """
        stmt = select(PromptUsageLog).order_by(desc(PromptUsageLog.timestamp)).limit(limit)
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                'id': r.id,
                'timestamp': r.timestamp.isoformat() if r.timestamp else None,
                'template_name': r.template_name,
                'hits': r.hits,
                'total_time_ms': r.total_time_ms,
                'avg_time_ms': r.avg_time_ms,
                'last_accessed': r.last_accessed.isoformat() if r.last_accessed else None,
                'error_count': r.error_count
            }
            for r in records
        ]

    @retry_on_lock()
    async def get_metrics_by_template(self, template_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        特定のテンプレートのメトリクス履歴を取得
        
        Args:
            template_name: テンプレート名
            limit: 取得する最大レコード数
            
        Returns:
            メトリクスの辞書リスト
        """
        stmt = select(PromptUsageLog).where(
            PromptUsageLog.template_name == template_name
        ).order_by(desc(PromptUsageLog.timestamp)).limit(limit)

        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                'id': r.id,
                'timestamp': r.timestamp.isoformat() if r.timestamp else None,
                'template_name': r.template_name,
                'hits': r.hits,
                'total_time_ms': r.total_time_ms,
                'avg_time_ms': r.avg_time_ms,
                'last_accessed': r.last_accessed.isoformat() if r.last_accessed else None,
                'error_count': r.error_count
            }
            for r in records
        ]

    @retry_on_lock()
    async def delete_old_metrics(self, days: int = 30) -> int:
        """
        指定日より古いメトリクスを削除
        
        Args:
            days: 保持する日数
            
        Returns:
            削除されたレコード数
        """
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)

        stmt = delete(PromptUsageLog).where(PromptUsageLog.timestamp < cutoff_date)
        result = await self.session.execute(stmt)
        return result.rowcount
