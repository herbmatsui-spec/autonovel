"""
src/models/narrative_metrics_db.py
物語定量的指標モデル。実体は src.backend.database.models.NarrativeMetric に統合済み。
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

# 本番ORMモデルへの統合エイリアス
from src.backend.database.models import NarrativeMetric

# プロトタイプ互換用ローカルBase（メインメタデータのテーブル名衝突を防止）
_LocalBase = declarative_base()


class NarrativeMetricLegacy(_LocalBase):
    """物語の定量的指標を保存する旧プロトタイプモデル"""

    __tablename__ = "narrative_metrics_legacy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, nullable=False, index=True)
    branch_id = Column(Integer, nullable=False, index=True)
    episode_num = Column(Integer, nullable=False)
    scene_num = Column(Integer, nullable=False)
    metric_name = Column(String(50), nullable=False)
    score = Column(Integer, nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class NarrativeMetricDefinition(_LocalBase):
    """指標の定義（ルーブリック）を保存するマスターモデル"""

    __tablename__ = "narrative_metric_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    rubric_text = Column(Text, nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


__all__ = ["NarrativeMetric", "NarrativeMetricLegacy", "NarrativeMetricDefinition"]
