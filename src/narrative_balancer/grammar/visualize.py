"""GraphViz DOT visualization for narrative parse forest."""

from src.narrative_balancer.grammar.parse_forest import ParseForest


def parse_forest_to_dot(forest: ParseForest) -> str:
    """Generate GraphViz DOT representation of the Earley parse forest."""
    lines = [
        "digraph ParseForest {",
        "  rankdir=TB;",
        "  node [fontname=\"Helvetica\"];",
    ]

    for k, item_set in enumerate(forest.chart):
        col_id = f"col_{k}"
        lines.append(f"  subgraph cluster_{k} {{")
        lines.append(f"    label=\"Position {k}\";")
        lines.append("    style=dashed; color=gray;")

        for idx, item in enumerate(item_set):
            node_id = f"item_{k}_{idx}"
            rule_str = " ".join(
                f".{sym.value}" if i == item.dot else sym.value
                for i, sym in enumerate(item.rule)
            )
            if item.dot == len(item.rule):
                rule_str += " ."

            label = f"{item.lhs.value} -> {rule_str} (orig={item.origin})"
            color = "green" if item.is_completed else "orange"
            lines.append(f"    {node_id} [label=\"{label}\", shape=box, color={color}];")

        lines.append("  }")

    lines.append("}")
    return "\n".join(lines)
