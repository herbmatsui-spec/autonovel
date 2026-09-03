"""multimedia artifacts and tasks

Revision ID: 0011_multimedia_artifacts
Revises: 0004_add_ai_assistant_config
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011_multimedia_artifacts"
down_revision = "0004_add_ai_assistant_config"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the current database."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("multimedia_artifacts"):
        op.create_table(
            "multimedia_artifacts",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("book_id", sa.Integer, nullable=False),
            sa.Column("asset_type", sa.String(50), nullable=False),
            sa.Column("format", sa.String(50), nullable=False),
            sa.Column("file_path", sa.String(1024), nullable=False),
            sa.Column("metadata_json", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )
        op.create_index(
            "ix_multimedia_artifacts_book_id",
            "multimedia_artifacts",
            ["book_id"],
        )
        op.create_index(
            "ix_multimedia_artifacts_asset_type",
            "multimedia_artifacts",
            ["asset_type"],
        )

    if not _table_exists("multimedia_tasks"):
        op.create_table(
            "multimedia_tasks",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("task_id", sa.String(64), nullable=False, unique=True),
            sa.Column("asset_id", sa.Integer, nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("started_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("finished_at", sa.DateTime, nullable=True),
            sa.Column("error", sa.Text, nullable=True),
        )
        op.create_index(
            "ix_multimedia_tasks_task_id",
            "multimedia_tasks",
            ["task_id"],
        )


def downgrade() -> None:
    if _table_exists("multimedia_tasks"):
        op.drop_table("multimedia_tasks")
    if _table_exists("multimedia_artifacts"):
        op.drop_table("multimedia_artifacts")