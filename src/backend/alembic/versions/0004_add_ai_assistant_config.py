"""add ai_assistant_config to books and user_preferences table

Revision ID: 0004_add_ai_assistant_config
Revises: 0003_pgvector_chapter_chunks
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_add_ai_assistant_config"
down_revision = "0003_pgvector_chapter_chunks"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the current database."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if table_name not in inspector.get_table_names():
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # SQLite互換: batch modeを使用
    if _table_exists("books") and not _column_exists("books", "ai_assistant_config"):
        with op.batch_alter_table("books", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "ai_assistant_config",
                    sa.JSON(),
                    nullable=False,
                    server_default='{"enabled": false, "auto_suggest": false, "trigger_mode": "manual", "features": {"continue": true, "describe": true, "rewrite": true}}',
                )
            )

    # user_preferences テーブル作成（存在しない場合のみ）
    if not _table_exists("user_preferences"):
        op.create_table(
            "user_preferences",
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("easy_mode_ai_enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("ai_features", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column(
                "updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()
            ),
            sa.PrimaryKeyConstraint("user_id"),
        )


def downgrade() -> None:
    if _table_exists("books") and _column_exists("books", "ai_assistant_config"):
        with op.batch_alter_table("books", schema=None) as batch_op:
            batch_op.drop_column("ai_assistant_config")
    if _table_exists("user_preferences"):
        op.drop_table("user_preferences")