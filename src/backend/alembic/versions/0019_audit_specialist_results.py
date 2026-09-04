"""create audit_specialist_results table

Revision ID: 0019_audit_specialist_results
Revises: 0018_create_book_scores

Phase 2: Multi-layer specialist audit results.
8 specialist auditors (consistency, creativity, reader_hook, emotion_curve,
style, factual, structure, multimodal) produce a 0-100 score, JSON feedback
and suggestions per chapter. Used by AuditAggregator to compute the
overall BookScore with weighted aggregation.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_audit_specialist_results"
down_revision = "0018_create_book_scores"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


SPECIALIST_NAMES = (
    "consistency",
    "creativity",
    "reader_hook",
    "emotion_curve",
    "style",
    "factual",
    "structure",
    "multimodal",
)


def upgrade() -> None:
    if _table_exists("audit_specialist_results"):
        return

    op.create_table(
        "audit_specialist_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("specialist_name", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("feedback_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("suggestions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        sa.Column("evaluator_version", sa.String(length=50), nullable=False, server_default="v2-phase2"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "book_id",
            "chapter_number",
            "specialist_name",
            name="uq_audit_specialist_results_book_chapter_specialist",
        ),
    )
    op.create_index(
        op.f("ix_audit_specialist_results_book_id"),
        "audit_specialist_results",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_specialist_results_chapter"),
        "audit_specialist_results",
        ["book_id", "chapter_number"],
        unique=False,
    )


def downgrade() -> None:
    if _table_exists("audit_specialist_results"):
        op.drop_index(
            op.f("ix_audit_specialist_results_chapter"),
            table_name="audit_specialist_results",
        )
        op.drop_index(
            op.f("ix_audit_specialist_results_book_id"),
            table_name="audit_specialist_results",
        )
        op.drop_table("audit_specialist_results")