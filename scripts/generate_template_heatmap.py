#!/usr/bin/env python3
"""
Step 22: Generate subtext template usage heatmap and statistical report (PLAN_Y2).
Outputs HTML report to reports/template_usage.html.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.matcher import ContextMatcher


def generate_heatmap(
    template_dir: Path = Path("templates/subtext"),
    report_path: Path = Path("reports/template_usage.html"),
) -> None:
    loader = TemplateLoader(template_dir)
    matcher = ContextMatcher()
    templates = loader.load_all()

    # Simulate realistic scene contexts
    test_contexts = [
        SubtextContext(emotion="betrayal", power_dynamic="inferior", relationship="former_ally"),
        SubtextContext(emotion="grief", power_dynamic="equal", relationship="lover"),
        SubtextContext(emotion="contempt", power_dynamic="superior", relationship="rival"),
        SubtextContext(emotion="longing", power_dynamic="equal", relationship="friend"),
        SubtextContext(emotion="tension", power_dynamic="equal", relationship="comrade", genre="comedy"),
        SubtextContext(emotion="vengeance", power_dynamic="superior", relationship="enemy", genre="horror"),
    ] * 20

    usage_counts: dict[str, int] = {tid: 0 for tid in templates}

    for i, ctx in enumerate(test_contexts):
        matched = matcher.match(list(templates.values()), ctx)
        if matched:
            selected = matcher.select(matched, ctx, seed=i * 13)
            if selected:
                usage_counts[selected.id] = usage_counts.get(selected.id, 0) + 1

    report_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for tid, count in sorted(usage_counts.items(), key=lambda x: x[1], reverse=True):
        cand = templates.get(tid)
        cat = cand.metadata.category if cand else "unknown"
        weight = cand.metadata.weight if cand else 0
        bar_width = min(100, count * 5)
        rows.append(
            f"<tr>"
            f"<td><code>{tid}</code></td>"
            f"<td>{cat}</td>"
            f"<td>{weight}</td>"
            f"<td><strong>{count}</strong></td>"
            f"<td><div style='background:#4f46e5; height:18px; width:{bar_width}%; border-radius:3px;'></div></td>"
            f"</tr>"
        )

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>Subtext Template Usage Heatmap</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }}
    h1 {{ color: #38bdf8; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; background: #1e293b; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; }}
    th {{ background: #0f172a; color: #94a3b8; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
    tr:hover {{ background: #334155; }}
    code {{ color: #a5b4fc; }}
  </style>
</head>
<body>
  <h1>Subtext Template Usage Heatmap</h1>
  <p>Total Simulated Turns: {len(test_contexts)} | Active Templates: {len(templates)}</p>
  <table>
    <thead>
      <tr><th>Template ID</th><th>Category</th><th>Weight</th><th>Usage Count</th><th>Distribution</th></tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    report_path.write_text(html_content, encoding="utf-8")
    print(f"Template heatmap successfully generated: {report_path.resolve()}")


if __name__ == "__main__":
    generate_heatmap()
