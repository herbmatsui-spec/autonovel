from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from database.core import Base


class NarrativeMetric(Base):
    """
    物語の定量的指標を保存するモデル
    """
    __tablename__ = "narrative_metrics"

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

    # 特定エピソードの時系列データ取得を高速化するための複合インデックス
    __table_args__ = (
        Index('ix_narrative_metrics_lookup', 'book_id', 'branch_id', 'episode_num', 'scene_num'),
    )

class NarrativeMetricDefinition(Base):
    """
    指標の定義（ルーブリック）を保存するマスターモデル
    """
    __tablename__ = "narrative_metric_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(String(50), unique=True, nullable=False) # 例: 'tension'
    display_name = Column(String(100), nullable=False) # 例: '緊張感'
    description = Column(Text, nullable=True)
    rubric_text = Column(Text, nullable=False) # LLMに渡す評価基準の詳細
    is_active = Column(Integer, default=1) # 1: 有効, 0: 無効
    created_at = Column(DateTime(timezone=True), server_default=func.now())
