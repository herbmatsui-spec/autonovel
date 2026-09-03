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
    op.execute("SELECT create_graph('autonovel_graph');")

    # Create label indexes for common entity types (improves MATCH performance)
    op.execute("""
        SELECT create_label_index('autonovel_graph', 'Character');
    """)
    op.execute("""
        SELECT create_label_index('autonovel_graph', 'Location');
    """)
    op.execute("""
        SELECT create_label_index('autonovel_graph', 'Item');
    """)
    op.execute("""
        SELECT create_label_index('autonovel_graph', 'Event');
    """)
    op.execute("""
        SELECT create_label_index('autonovel_graph', 'Faction');
    """)
    op.execute("""
        SELECT create_label_index('autonovel_graph', 'Concept');
    """)

    # Create property index on 'name' for all labels (used by MERGE)
    op.execute("""
        SELECT create_property_index('autonovel_graph', 'Character', 'name');
    """)
    op.execute("""
        SELECT create_property_index('autonovel_graph', 'Location', 'name');
    """)
    op.execute("""
        SELECT create_property_index('autonovel_graph', 'Item', 'name');
    """)
    op.execute("""
        SELECT create_property_index('autonovel_graph', 'Event', 'name');
    """)
    op.execute("""
        SELECT create_property_index('autonovel_graph', 'Faction', 'name');
    """)
    op.execute("""
        SELECT create_property_index('autonovel_graph', 'Concept', 'name');
    """)


def downgrade() -> None:
    if not _is_postgres():
        return

    # Drop property indexes
    op.execute("""
        SELECT drop_property_index('autonovel_graph', 'Character', 'name');
    """)
    op.execute("""
        SELECT drop_property_index('autonovel_graph', 'Location', 'name');
    """)
    op.execute("""
        SELECT drop_property_index('autonovel_graph', 'Item', 'name');
    """)
    op.execute("""
        SELECT drop_property_index('autonovel_graph', 'Event', 'name');
    """)
    op.execute("""
        SELECT drop_property_index('autonovel_graph', 'Faction', 'name');
    """)
    op.execute("""
        SELECT drop_property_index('autonovel_graph', 'Concept', 'name');
    """)

    # Drop label indexes
    op.execute("""
        SELECT drop_label_index('autonovel_graph', 'Character');
    """)
    op.execute("""
        SELECT drop_label_index('autonovel_graph', 'Location');
    """)
    op.execute("""
        SELECT drop_label_index('autonovel_graph', 'Item');
    """)
    op.execute("""
        SELECT drop_label_index('autonovel_graph', 'Event');
    """)
    op.execute("""
        SELECT drop_label_index('autonovel_graph', 'Faction');
    """)
    op.execute("""
        SELECT drop_label_index('autonovel_graph', 'Concept');
    """)

    # Drop graph (cascade removes all data)
    op.execute("SELECT drop_graph('autonovel_graph', true);")
