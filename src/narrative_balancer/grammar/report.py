"""Cost breakdown and grammar diagnostics report generator."""

from src.narrative_balancer.grammar.dp_engine import GrammarAnalysisResult


def generate_cost_report(analysis: GrammarAnalysisResult) -> str:
    """Format analysis result into a structured Markdown diagnostic report."""
    pending_list = ", ".join(nt.value for nt in analysis.pending_nonterminals) or "None (Clean)"

    md = [
        "# 物語文法・DPコスト解析レポート",
        "",
        f"- **解析話数**: {analysis.total_episodes} 話",
        f"- **プレフィックス妥当性**: {'正常 (Valid Prefix)' if analysis.is_valid_prefix else '破綻/未知パターン'}",
        f"- **未完了非終端記号 (Pending Rules)**: {pending_list}",
        f"- **最小完結推定コスト**: {analysis.completion_cost:.2f}",
        f"- **総合成コスト (Total Cost)**: {analysis.total_cost:.2f}",
        "",
        "## ペナルティ内訳",
        "",
        "| 評価項目 | ペナルティ値 | 状態 |",
        "|---|---|---|",
    ]

    for key, val in analysis.penalties.items():
        status = "良好" if val == 0 else "要改善"
        md.append(f"| {key} | {val:.2f} | {status} |")

    return "\n".join(md)
