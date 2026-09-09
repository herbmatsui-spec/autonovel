"""initial migration

Revision ID: 0000_initial_migration
Revises:
"""

from __future__ import annotations


from alembic import op


revision = "0000_initial_migration"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create initial tables from ORM models if they don't exist
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64);")
    import src.backend.database.models  # noqa: F401
    import src.infrastructure.database.models  # noqa: F401
    from src.infrastructure.database.models.base_orm import Base

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    # Placeholder for downgrade
    pass
