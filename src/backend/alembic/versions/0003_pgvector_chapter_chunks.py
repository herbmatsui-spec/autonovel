"""pgvector 拡張と ivfflat インデックス.

PostgreSQL でのみ実 DDL を実行し、SQLite では no-op。
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0003_pgvector_chapter_chunks"
down_revision = "0002_add_catchcopy"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        # SQLite fallback: column already exists as JSON; nothing to do.
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute(
        "ALTER TABLE chapter_chunks "
        "ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chapter_chunks_embedding "
        "ON chapter_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute("DROP INDEX IF EXISTS ix_chapter_chunks_embedding;")
    # We do not drop the extension or revert the column type to JSON because
    # other tables may rely on it.
