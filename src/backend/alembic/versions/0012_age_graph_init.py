"""Apache AGE graph initialization and indexes.

PostgreSQL only: creates AGE graph, labels, and property indexes.
"""

from __future__ import annotations

from alembic import op


revision = "0012_age_graph_init"
down_revision = "0011_multimedia_artifacts"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    # Ensure extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS age;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("LOAD 'age';")
    op.execute('SET search_path = ag_catalog, "$user", public;')

    # Create default graph (idempotent)
    op.execute("""
        DO '
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = ''autonovel_graph'') THEN
                PERFORM ag_catalog.create_graph(''autonovel_graph'');
            END IF;
        END;';
    """)

    # Create vertex labels and property indexes for common entity types
    labels = ["Character", "Location", "Item", "Event", "Faction", "Concept"]
    for label in labels:
        op.execute(f"""
            DO '
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM ag_catalog.ag_label 
                    WHERE name = ''{label}'' 
                    AND graph = (SELECT graphid FROM ag_catalog.ag_graph WHERE name = ''autonovel_graph'')
                ) THEN
                    PERFORM ag_catalog.create_vlabel(''autonovel_graph'', ''{label}'');
                END IF;
            END;';
        """)
        op.execute(f"""
            CREATE INDEX IF NOT EXISTS "ix_{label}_properties" 
            ON autonovel_graph."{label}" USING gin (properties);
        """)


def downgrade() -> None:
    if not _is_postgres():
        return

    labels = ["Character", "Location", "Item", "Event", "Faction", "Concept"]
    for label in labels:
        op.execute(f'DROP INDEX IF EXISTS autonovel_graph."ix_{label}_properties";')

    op.execute("""
        DO '
        BEGIN
            IF EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = ''autonovel_graph'') THEN
                PERFORM ag_catalog.drop_graph(''autonovel_graph'', true);
            END IF;
        END;';
    """)
