"""create rag_reflection_history table

Revision ID: 0020_rag_reflection_history
Revises: 0019_audit_specialist_results

Phase 2: Reflective RAG screening history.
Stores each reflective retrieval attempt: original query, refined queries
JSON array, iterations count, final document count, and convergence flag.
Used for offline analysis (iterations avg, convergence rate, filter rate).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020_rag_reflection_history"
down_revision = "0019_audit_specialist_results"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _table_exists("rag_reflection_history"):
        return

    op.create_table(
        "rag_reflection_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=True),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("refined_queries_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("iterations", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("initial_doc_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_doc_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("converged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rag_reflection_history_book_id"),
        "rag_reflection_history",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_reflection_history_session"),
        "rag_reflection_history",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_reflection_history_created"),
        "rag_reflection_history",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    if _table_exists("rag_reflection_history"):
        op.drop_index(
            op.f("ix_rag_reflection_history_created"),
            table_name="rag_reflection_history",
        )
        op.drop_index(
            op.f("ix_rag_reflection_history_session"),
            table_name="rag_reflection_history",
        )
        op.drop_index(
            op.f("ix_rag_reflection_history_book_id"),
            table_name="rag_reflection_history",
        )
        op.drop_table("rag_reflection_history")