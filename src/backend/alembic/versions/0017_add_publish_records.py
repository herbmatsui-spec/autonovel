"""add publish_records table

Revision ID: 0017_add_publish_records
Revises: 0016_add_branch_play_sessions
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0017_add_publish_records"
down_revision = "0016_add_branch_play_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publish_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("book_id", sa.Integer, nullable=False),
        sa.Column("episode_num", sa.Integer, nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("post_id", sa.String(255), nullable=False),
        sa.Column("post_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="published"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_publish_record_book_ep_platform",
        "publish_records",
        ["book_id", "episode_num", "platform"],
    )
    op.create_index(
        "ix_publish_record_book_platform",
        "publish_records",
        ["book_id", "platform"],
    )
    op.create_index(
        "ix_publish_record_book_id",
        "publish_records",
        ["book_id"],
    )
    op.create_index(
        "ix_publish_record_platform",
        "publish_records",
        ["platform"],
    )


def downgrade() -> None:
    op.drop_index("ix_publish_record_platform", table_name="publish_records")
    op.drop_index("ix_publish_record_book_id", table_name="publish_records")
    op.drop_index("ix_publish_record_book_platform", table_name="publish_records")
    op.drop_constraint("uq_publish_record_book_ep_platform", "publish_records", type_="unique")
    op.drop_table("publish_records")
