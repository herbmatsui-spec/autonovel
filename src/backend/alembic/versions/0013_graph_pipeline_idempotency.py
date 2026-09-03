"""Graph pipeline idempotency table.

PostgreSQL only: creates table for tracking processed chapters.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_graph_pipeline_idempotency"
down_revision = "0012_age_graph_init"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    op.create_table(
        "graph_pipeline_idempotency",
        sa.Column("idempotency_key", sa.String(128), primary_key=True),
        sa.Column("chapter_id", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_graph_pipeline_idempotency_chapter_id",
        "graph_pipeline_idempotency",
        ["chapter_id"],
    )


def downgrade() -> None:
    if not _is_postgres():
        return

    op.drop_index("ix_graph_pipeline_idempotency_chapter_id", table_name="graph_pipeline_idempotency")
    op.drop_table("graph_pipeline_idempotency")