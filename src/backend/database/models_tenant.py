"""
src/backend/database/models_tenant.py — マルチテナンシー・組織管理ORMモデル
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from src.infrastructure.database.models.base_orm import Base


class Tenant(Base):
    """組織・テナントエンティティ（Phase 2 マルチテナント拡張用基盤）。"""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    plan_tier = Column(String(20), default="free", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    members = relationship("TenantMember", back_populates="tenant", cascade="all, delete-orphan")


class TenantMember(Base):
    """テナントメンバーシップおよびロール定義。"""

    __tablename__ = "tenant_members"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), default="member", nullable=False)  # owner, admin, member, viewer
    created_at = Column(DateTime, server_default=func.now())

    tenant = relationship("Tenant", back_populates="members")
