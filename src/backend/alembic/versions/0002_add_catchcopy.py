"""add catchcopy to books

Revision ID: 0002_add_catchcopy
Revises: 0001_erotic_intensity
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_add_catchcopy"
down_revision = "0001_erotic_intensity"
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
    if _table_exists("books") and not _column_exists("books", "catchcopy"):
        with op.batch_alter_table("books", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("catchcopy", sa.String(255), nullable=True, server_default="")
            )


def downgrade() -> None:
    if _table_exists("books") and _column_exists("books", "catchcopy"):
        with op.batch_alter_table("books", schema=None) as batch_op:
            batch_op.drop_column("catchcopy")