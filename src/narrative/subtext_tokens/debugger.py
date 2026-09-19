"""
Subtext Token Debugger and Diff Visualizer (PLAN_Y3 Step 16).
Outputs colored HTML comparison between raw generated text and token-expanded post-processed text.
"""

from __future__ import annotations

import difflib
import html
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.narrative.subtext_tokens.parser import TOKEN_REGEX


class TokenDebugger:
    """Visualizes token expansion and generates HTML comparison diffs."""

    @staticmethod
    def highlight_tokens(text: str) -> str:
        """Wraps [CATEGORY:KEY:MODIFIER] in styled HTML span tags."""
        def repl(m: Any) -> str:
            raw = html.escape(m.group(0))
            return f"<span style='background:#4338ca; color:#e0e7ff; padding:2px 6px; border-radius:4px; font-weight:bold;'>{raw}</span>"

        return TOKEN_REGEX.sub(repl, html.escape(text))

    @classmethod
    def generate_html_diff(
        cls,
        raw_text: str,
        processed_text: str,
        output_path: Optional[str | Path] = None,
    ) -> str:
        raw_highlighted = cls.highlight_tokens(raw_text).replace("\n", "<br>")
        proc_escaped = html.escape(processed_text).replace("\n", "<br>")

        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>Subtext Token Expansion Diff</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }}
    h1 {{ color: #38bdf8; }}
    .container {{ display: flex; gap: 2rem; margin-top: 1.5rem; }}
    .panel {{ flex: 1; background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155; }}
    h2 {{ font-size: 1.1rem; color: #94a3b8; margin-bottom: 1rem; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; }}
    .content {{ line-height: 1.8; font-size: 0.95rem; font-family: monospace; }}
  </style>
</head>
<body>
  <h1>Subtext Token Expansion Diff Report</h1>
  <div class="container">
    <div class="panel">
      <h2>1. Raw Generation with Control Tokens</h2>
      <div class="content">{raw_highlighted}</div>
    </div>
    <div class="panel">
      <h2>2. Post-Processed Expanded Text</h2>
      <div class="content">{proc_escaped}</div>
    </div>
  </div>
</body>
</html>
"""
        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(html_content, encoding="utf-8")

        return html_content
