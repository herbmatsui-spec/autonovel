"""create pdca_history_snapshots table

Revision ID: 0022_pdca_history
Revises: 0021_publication_schedules

Phase 1: BookScore/PDCA Dashboard.
Stores detailed snapshots of each PDCA regeneration cycle for trend analysis and auditing.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022_pdca_history"
down_revision = "0021_publication_schedules"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _table_exists("pdca_history_snapshots"):
        return

    op.create_table(
        "pdca_history_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("initial_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("score_delta", sa.Float(), nullable=False),
        sa.Column("improved_percentage", sa.Float(), nullable=False),
        sa.Column("lowest_dimension", sa.String(length=100), nullable=False),
        sa.Column("directives", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("converged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pdca_history_snapshots_book_id"),
        "pdca_history_snapshots",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        "idx_pdca_history_book_chap",
        "pdca_history_snapshots",
        ["book_id", "chapter_number"],
        unique=False,
    )


def downgrade() -> None:
    if _table_exists("pdca_history_snapshots"):
        op.drop_index(op.f("ix_pdca_history_snapshots_book_id"), table_name="pdca_history_snapshots")
        op.drop_index("idx_pdca_history_book_chap", table_name="pdca_history_snapshots")
        op.drop_table("pdca_history_snapshots")
