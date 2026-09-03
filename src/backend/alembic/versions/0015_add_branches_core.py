"""add branches core table (IF ルート分岐システム用)

Revision ID: 0015_add_branches_core
Revises: 0014_add_patch_review_and_setting_version

Note:
    Branch ORM は src/backend/database/models.py に既に存在し、
    Base.metadata.create_all() で動的に作成されている。
    本マイグレーションは Alembic 経路でも同等のスキーマを再現し、
    test_migrations.py::test_migrations_up_down が要求する
    "branches" テーブルを Alembic 経由でも作成できるようにする。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0015_add_branches_core"
down_revision = "0014_add_patch_review_and_setting_version"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the current database."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("branches"):
        op.create_table(
            "branches",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("fork_ep_num", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("graph_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )
        op.create_index("idx_branches_book_id", "branches", ["book_id"])
        op.create_index("idx_branches_parent_id", "branches", ["parent_id"])


def downgrade() -> None:
    if _table_exists("branches"):
        op.drop_table("branches")