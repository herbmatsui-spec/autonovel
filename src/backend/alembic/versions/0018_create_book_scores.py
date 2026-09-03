"""create book_scores table

Revision ID: 0018_create_book_scores
Revises: 0017_add_publish_records
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_create_book_scores"
down_revision = "0017_add_publish_records"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the current database."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("book_scores"):
        op.create_table(
            "book_scores",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
            sa.Column("chapter_number", sa.Integer(), nullable=False),
            sa.Column("overall_score", sa.Float(), nullable=False),
            sa.Column("structure_score", sa.Float(), nullable=False),
            sa.Column("coherency_score", sa.Float(), nullable=False),
            sa.Column("factual_grounding_score", sa.Float(), nullable=False),
            sa.Column("visual_textual_synergy_score", sa.Float(), nullable=False),
            sa.Column("reader_experience_score", sa.Float(), nullable=False),
            sa.Column("evaluated_at", sa.DateTime(), nullable=False),
            sa.Column("evaluator_version", sa.String(length=50), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_book_scores_book_id"), "book_scores", ["book_id"], unique=False)


def downgrade() -> None:
    if _table_exists("book_scores"):
        op.drop_index(op.f("ix_book_scores_book_id"), table_name="book_scores")
        op.drop_table("book_scores")