#!/usr/bin/env python
"""DI Graph Visualization - Pure Python Implementation"""

import json


def generate_di_svg() -> str:
    """Generate SVG directly without external dependencies."""

    # DI Graph data structure
    providers = {
        'api_key': {'type': 'ObjectProvider', 'deps': []},
        'db': {'type': 'SingletonProvider', 'deps': ['get_db_manager']},
        'vector_store': {'type': 'SingletonProvider', 'deps': []},
        'audit_logger': {'type': 'SingletonProvider', 'deps': []},
        'cooldown': {'type': 'SingletonProvider', 'deps': []},
        'genai_client': {'type': 'SingletonProvider', 'deps': ['create_genai_client', 'api_key']},
        'llm_factory': {'type': 'SingletonProvider', 'deps': ['LLMProviderFactory', 'genai_client', 'cooldown']},
        'semantic_cache': {'type': 'SingletonProvider', 'deps': ['SemanticCacheManager', 'vector_store', 'llm_client']},
        'llm': {'type': 'SingletonProvider', 'deps': ['LLMGenerateResultProxy', 'llm_factory']},
        'connection_pipeline': {'type': 'SingletonProvider', 'deps': ['_get_connection_pipeline']},
        'repo': {'type': 'SingletonProvider', 'deps': ['DataRepository', 'db']},
        'uow': {'type': 'FactoryProvider', 'deps': ['UnitOfWork', 'db']},
        'pm': {'type': 'SingletonProvider', 'deps': ['PromptManager']},
        'ctx_mgr': {'type': 'SingletonProvider', 'deps': ['ContextManager', 'repo']},
        'global_config': {'type': 'SingletonProvider', 'deps': ['get_config']},
        'auditor': {'type': 'SingletonProvider', 'deps': ['LogicalAuditor', 'repo', 'pm', 'llm', 'ctx_mgr']},
        'marketing': {'type': 'SingletonProvider', 'deps': ['MarketingAgent', 'repo', 'pm', 'llm']},
        'bible_generator': {'type': 'SingletonProvider', 'deps': ['WorldBibleGenerator', 'repo', 'llm', 'pm', 'marketing', 'auditor']},
        'plot_expander': {'type': 'SingletonProvider', 'deps': ['PlotExpander', 'repo', 'llm', 'pm', 'auditor']},
        'planner': {'type': 'SingletonProvider', 'deps': ['PlanningAgent', 'repo', 'pm', 'ctx_mgr', 'auditor', 'bible_generator', 'plot_expander']},
        'validator': {'type': 'SingletonProvider', 'deps': ['LogicalAuditor', 'repo', 'pm', 'llm', 'ctx_mgr']},
        'narrative': {'type': 'SingletonProvider', 'deps': ['NarrativeController', 'llm', 'repo', 'pm', 'ctx_mgr', 'validator', 'auditor']},
        'critique': {'type': 'SingletonProvider', 'deps': ['CritiqueAgent', 'repo', 'pm', 'llm']},
        'style_rag': {'type': 'SingletonProvider', 'deps': ['StyleRagManager', 'genai_client', 'repo']},
        'writer': {'type': 'SingletonProvider', 'deps': ['WritingAgent', 'repo', 'llm', 'pm', 'ctx_mgr', 'narrative', 'critique', 'plot_expander', 'style_rag', 'uow', 'global_config', 'planner']},
        'formatter': {'type': 'SingletonProvider', 'deps': ['KakuyomuFormatter']},
    }

    # Generate SVG markup
    svg_parts = [
        '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">
<style>
.node { fill: #e8f4fd; stroke: #2563eb; stroke-width: 2; rx: 8; ry: 8; font-family: Arial, sans-serif; font-size: 11px; }
.edge { stroke: #64748b; stroke-width: 1.5; marker-end: url(#arrowhead); }
.title { font-family: Arial, sans-serif; font-size: 18px; font-weight: bold; fill: #1e293b; }
</style>
<defs>
  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#64748b"/>
  </marker>
</defs>
<text x="600" y="30" text-anchor="middle" class="title">DI Container Dependency Graph</text>
<g transform="translate(50, 60)">
''']

    # Position nodes in grid layout
    positions = {}
    cols = 6
    x_spacing = 180
    y_spacing = 60

    for i, (name, info) in enumerate(providers.items()):
        col = i % cols
        row = i // cols
        x = col * x_spacing
        y = row * y_spacing
        positions[name] = (x, y)

        label = f'{name}\\n({info["type"].split("Provider")[0]}...)'
        svg_parts.append(f'''  <g id="{name}">
    <rect class="node" x="{x}" y="{y}" width="140" height="40"/>
    <text x="{x+70}" y="{y+25}" text-anchor="middle" dominant-baseline="middle">{label}</text>
  </g>
''')

    # Add edges
    svg_parts.append('  <g id="edges">\\n')
    for name, info in providers.items():
        src_x, src_y = positions[name]
        for dep in info['deps']:
            if dep in positions:
                dst_x, dst_y = positions[dep]
                svg_parts.append(f'''    <line x1="{src_x+70}" y1="{src_y+40}" x2="{dst_x+70}" y2="{dst_y}" class="edge"/>
''')

    svg_parts.append('  </g>\\n</g>\\n</svg>')

    return '\\n'.join(svg_parts)

if __name__ == '__main__':
    svg_content = generate_di_svg()
    with open('docs/di_graph_20260707.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print('SVG saved to docs/di_graph_20260707.svg')

    # Also save as JSON for programmatic access
    with open('docs/di_graph_20260707.json', 'w', encoding='utf-8') as f:
        json.dump({
            'providers': {k: {'type': v['type']} for k, v in {
                'api_key': {'type': 'ObjectProvider', 'deps': []},
                'db': {'type': 'SingletonProvider', 'deps': ['get_db_manager']},
                'vector_store': {'type': 'SingletonProvider', 'deps': []},
                'audit_logger': {'type': 'SingletonProvider', 'deps': []},
                'cooldown': {'type': 'SingletonProvider', 'deps': []},
                'genai_client': {'type': 'SingletonProvider', 'deps': ['create_genai_client', 'api_key']},
                'llm_factory': {'type': 'SingletonProvider', 'deps': ['LLMProviderFactory', 'genai_client', 'cooldown']},
                'semantic_cache': {'type': 'SingletonProvider', 'deps': ['SemanticCacheManager', 'vector_store', 'llm_client']},
                'llm': {'type': 'SingletonProvider', 'deps': ['LLMGenerateResultProxy', 'llm_factory']},
                'connection_pipeline': {'type': 'SingletonProvider', 'deps': ['_get_connection_pipeline']},
                'repo': {'type': 'SingletonProvider', 'deps': ['DataRepository', 'db']},
                'uow': {'type': 'FactoryProvider', 'deps': ['UnitOfWork', 'db']},
                'pm': {'type': 'SingletonProvider', 'deps': ['PromptManager']},
                'ctx_mgr': {'type': 'SingletonProvider', 'deps': ['ContextManager', 'repo']},
                'global_config': {'type': 'SingletonProvider', 'deps': ['get_config']},
                'auditor': {'type': 'SingletonProvider', 'deps': ['LogicalAuditor', 'repo', 'pm', 'llm', 'ctx_mgr']},
                'marketing': {'type': 'SingletonProvider', 'deps': ['MarketingAgent', 'repo', 'pm', 'llm']},
                'bible_generator': {'type': 'SingletonProvider', 'deps': ['WorldBibleGenerator', 'repo', 'llm', 'pm', 'marketing', 'auditor']},
                'plot_expander': {'type': 'SingletonProvider', 'deps': ['PlotExpander', 'repo', 'llm', 'pm', 'auditor']},
                'planner': {'type': 'SingletonProvider', 'deps': ['PlanningAgent', 'repo', 'pm', 'ctx_mgr', 'auditor', 'bible_generator', 'plot_expander']},
                'validator': {'type': 'SingletonProvider', 'deps': ['LogicalAuditor', 'repo', 'pm', 'llm', 'ctx_mgr']},
                'narrative': {'type': 'SingletonProvider', 'deps': ['NarrativeController', 'llm', 'repo', 'pm', 'ctx_mgr', 'validator', 'auditor']},
                'critique': {'type': 'SingletonProvider', 'deps': ['CritiqueAgent', 'repo', 'pm', 'llm']},
                'style_rag': {'type': 'SingletonProvider', 'deps': ['StyleRagManager', 'genai_client', 'repo']},
                'writer': {'type': 'SingletonProvider', 'deps': ['WritingAgent', 'repo', 'llm', 'pm', 'ctx_mgr', 'narrative', 'critique', 'plot_expander', 'style_rag', 'uow', 'global_config', 'planner']},
                'formatter': {'type': 'SingletonProvider', 'deps': ['KakuyomuFormatter']},
            }},
            'edges': {k: v['deps'] for k, v in {
                'llm_factory': {'type': 'SingletonProvider', 'deps': ['LLMProviderFactory', 'genai_client', 'cooldown']},
                'semantic_cache': {'type': 'SingletonProvider', 'deps': ['SemanticCacheManager', 'vector_store', 'llm_client']},
                'auditor': {'type': 'SingletonProvider', 'deps': ['LogicalAuditor', 'repo', 'pm', 'llm', 'ctx_mgr']},
                'marketing': {'type': 'SingletonProvider', 'deps': ['MarketingAgent', 'repo', 'pm', 'llm']},
                'bible_generator': {'type': 'SingletonProvider', 'deps': ['WorldBibleGenerator', 'repo', 'llm', 'pm', 'marketing', 'auditor']},
                'plot_expander': {'type': 'SingletonProvider', 'deps': ['PlotExpander', 'repo', 'llm', 'pm', 'auditor']},
                'planner': {'type': 'SingletonProvider', 'deps': ['PlanningAgent', 'repo', 'pm', 'ctx_mgr', 'auditor', 'bible_generator', 'plot_expander']},
                'narrative': {'type': 'SingletonProvider', 'deps': ['NarrativeController', 'llm', 'repo', 'pm', 'ctx_mgr', 'validator', 'auditor']},
                'critique': {'type': 'SingletonProvider', 'deps': ['CritiqueAgent', 'repo', 'pm', 'llm']},
                'style_rag': {'type': 'SingletonProvider', 'deps': ['StyleRagManager', 'genai_client', 'repo']},
                'writer': {'type': 'SingletonProvider', 'deps': ['WritingAgent', 'repo', 'llm', 'pm', 'ctx_mgr', 'narrative', 'critique', 'plot_expander', 'style_rag', 'uow', 'global_config', 'planner']},
            }}
        }, f, indent=2, ensure_ascii=False)

    print('JSON saved to docs/di_graph_20260707.json')
