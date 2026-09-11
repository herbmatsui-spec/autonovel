"""0026_audio_assets.py

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audio_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("episode_num", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_audio_assets_book_ep", "audio_assets", ["book_id", "episode_num"])


def downgrade():
    op.drop_index("idx_audio_assets_book_ep", table_name="audio_assets")
    op.drop_table("audio_assets")
