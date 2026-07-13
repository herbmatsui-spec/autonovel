#!/usr/bin/env python
"""DI Graph Visualization - Generate SVG/PNG from DOT format"""

import graphviz

# Create a directed graph
dot = graphviz.Digraph(comment='DI Graph - Hegemony Novel Engine')

# Add nodes for providers
providers = [
    ('api_key', 'ObjectProvider'),
    ('db', 'SingletonProvider'),
    ('vector_store', 'SingletonProvider'),
    ('audit_logger', 'SingletonProvider'),
    ('cooldown', 'SingletonProvider'),
    ('genai_client', 'SingletonProvider'),
    ('llm_factory', 'SingletonProvider'),
    ('semantic_cache', 'SingletonProvider'),
    ('llm', 'SingletonProvider'),
    ('repo', 'SingletonProvider'),
    ('uow', 'FactoryProvider'),
    ('pm', 'SingletonProvider'),
    ('ctx_mgr', 'SingletonProvider'),
    ('auditor', 'SingletonProvider'),
    ('marketing', 'SingletonProvider'),
    ('bible_generator', 'SingletonProvider'),
    ('plot_expander', 'SingletonProvider'),
    ('planner', 'SingletonProvider'),
    ('narrative', 'SingletonProvider'),
    ('critique', 'SingletonProvider'),
    ('style_rag', 'SingletonProvider'),
    ('writer', 'SingletonProvider'),
]

for name, ptype in providers:
    dot.node(name, f'{name}\n({ptype})')

# Add edges for dependencies
edges = [
    ('llm_factory', 'genai_client'),
    ('llm_factory', 'cooldown'),
    ('semantic_cache', 'vector_store'),
    ('semantic_cache', 'genai_client'),
    ('repo', 'db'),
    ('ctx_mgr', 'repo'),
    ('auditor', 'repo'),
    ('auditor', 'pm'),
    ('auditor', 'llm'),
    ('marketing', 'repo'),
    ('marketing', 'pm'),
    ('marketing', 'llm'),
    ('bible_generator', 'repo'),
    ('bible_generator', 'llm'),
    ('bible_generator', 'pm'),
    ('bible_generator', 'auditor'),
    ('plot_expander', 'repo'),
    ('plot_expander', 'llm'),
    ('plot_expander', 'pm'),
    ('plot_expander', 'auditor'),
    ('planner', 'repo'),
    ('planner', 'pm'),
    ('planner', 'auditor'),
    ('writer', 'repo'),
    ('writer', 'llm'),
    ('writer', 'pm'),
    ('writer', 'planner'),
]

for src, dst in edges:
    dot.edge(src, dst)

# Save the graph
dot.render('docs/di_graph_20260707', format='svg', cleanup=True)
dot.render('docs/di_graph_20260707', format='png', cleanup=True)
print('Graph saved to docs/di_graph_20260707.svg and .png')
