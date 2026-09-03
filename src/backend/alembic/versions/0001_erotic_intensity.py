"""add erotic_intensity to plot

Revision ID: 0001_erotic_intensity
Revises: 0000_initial_migration
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_erotic_intensity"
down_revision = "0000_initial_migration"
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
    # plots テーブルが存在し、erotic_intensity カラムが未追加の場合のみ追加
    if _table_exists("plots") and not _column_exists("plots", "erotic_intensity"):
        with op.batch_alter_table("plots", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("erotic_intensity", sa.Integer(), nullable=True, server_default="0")
            )


def downgrade() -> None:
    # plots テーブルが存在し、erotic_intensity カラムが存在する場合のみ削除
    if _table_exists("plots") and _column_exists("plots", "erotic_intensity"):
        with op.batch_alter_table("plots", schema=None) as batch_op:
            batch_op.drop_column("erotic_intensity")