from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, text
from src.infrastructure.database.models.base_orm import Base
from sqlalchemy.sql import func

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: int = Column(Integer, nullable=False)  # 消費は負数、付与は正数
    balance_after: int = Column(Integer, nullable=False)
    transaction_type = Column(String(30), nullable=False)
    task_id = Column(String(100), nullable=True, index=True)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    stripe_subscription_id = Column(String(255), unique=True, nullable=False, index=True)
    stripe_customer_id = Column(String(255), nullable=False)
    plan_tier = Column(String(20), nullable=False)
    status = Column(String(30), nullable=False)  # active, canceled, past_due
    current_period_end = Column(DateTime, nullable=False)


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    event_id = Column(String(255), primary_key=True)
    event_type = Column(String(100), nullable=False)
    status = Column(String(30), default="processed", nullable=False)  # processing, processed, failed
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, server_default=func.now(), onupdate=func.now())