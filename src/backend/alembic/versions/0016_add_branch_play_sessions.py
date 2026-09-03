"""add branch_play_sessions table (IF ルートプレイヤーセッション保存用)

Revision ID: 0016_add_branch_play_sessions
Revises: 0015_add_branches_core
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0016_add_branch_play_sessions"
down_revision = "0015_add_branches_core"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the current database."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("branch_play_sessions"):
        op.create_table(
            "branch_play_sessions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("book_id", sa.Integer(), nullable=False),
            sa.Column("branch_id", sa.Integer(), nullable=False),
            sa.Column("current_node_id", sa.String(255), nullable=True),
            sa.Column("context_json", sa.JSON(), nullable=True),
            sa.Column("save_points_json", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(20), nullable=True, server_default="active"),
            sa.Column("version", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )
        op.create_index("idx_bps_book_branch", "branch_play_sessions", ["book_id", "branch_id"])
        op.create_index("idx_bps_status", "branch_play_sessions", ["status"])


def downgrade() -> None:
    if _table_exists("branch_play_sessions"):
        op.drop_table("branch_play_sessions")