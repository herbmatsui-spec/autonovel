"""create publication_schedules table

Revision ID: 0021_publication_schedules
Revises: 0020_rag_reflection_history

Phase 1: Commercial Publication Scheduling.
Stores scheduled publication dates, platforms, and episode ranges for books.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021_publication_schedules"
down_revision = "0020_rag_reflection_history"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _table_exists("publication_schedules"):
        return

    op.create_table(
        "publication_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("episode_range_start", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("episode_range_end", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("post_id", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_publication_schedules_book_id"),
        "publication_schedules",
        ["book_id"],
        unique=False,
    )


def downgrade() -> None:
    if _table_exists("publication_schedules"):
        op.drop_index(op.f("ix_publication_schedules_book_id"), table_name="publication_schedules")
        op.drop_table("publication_schedules")
