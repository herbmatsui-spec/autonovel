from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CostLogModel(Base):
    """LLM API 呼び出しごとのコストを記録するモデル。"""

    __tablename__ = "cost_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    model_name = Column(String(255), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    provider = Column(String(100), nullable=False)
    task_type = Column(String(100), default="unknown")
    success = Column(Integer, default=1)  # 1=成功, 0=失敗
    error_message = Column(Text, nullable=True)


class BudgetModel(Base):
    """予算設定モデル。"""

    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), unique=True, nullable=False)
    limit_usd = Column(Float, nullable=False)
    threshold_percentage = Column(Float, default=90.0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)