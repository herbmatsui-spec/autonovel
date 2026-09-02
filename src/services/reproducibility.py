"""
services/reproducibility.py - 生成ログ・Trace ID 再現性レポート

各生成処理のメタデータ（プロンプトバージョン/モデル/パラメータ/入力ハッシュ/
Trace ID）を記録し、同一条件での再現性を証明するレポートを生成する。
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_input_hash(payload: dict[str, Any]) -> str:
    """入力ペイロードの SHA256 ハッシュを計算する。"""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_run_record(
    book_id: int,
    task_type: str,
    prompt_version: str,
    model_name: str,
    params: dict[str, Any],
    payload: dict[str, Any],
    output_preview: str = "",
    trace_id: str = "",
    chapter_ep: int | None = None,
) -> dict[str, Any]:
    """GenerationRun のレコード辞書を構築する。"""
    return {
        "book_id": book_id,
        "chapter_ep": chapter_ep,
        "task_type": task_type,
        "prompt_version": prompt_version,
        "model_name": model_name,
        "params_json": json.dumps(params, ensure_ascii=False, default=str),
        "input_hash": compute_input_hash(payload),
        "output_preview": (output_preview or "")[:500],
        "trace_id": trace_id,
    }


def build_report(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """再現性レポート（Markdown + メタデータ）を構築する。"""
    lines = ["# 生成再現性レポート", ""]
    lines.append(f"記録数: {len(runs)}")
    lines.append("")
    for r in runs:
        lines.append(f"## タスク: {r.get('task_type')} (第{r.get('chapter_ep')}話)")
        lines.append(f"- Trace ID: `{r.get('trace_id')}`")
        lines.append(f"- プロンプト版: {r.get('prompt_version')}")
        lines.append(f"- モデル: {r.get('model_name')}")
        lines.append(f"- パラメータ: {r.get('params_json')}")
        lines.append(f"- 入力ハッシュ: `{r.get('input_hash')}`")
        lines.append("")
    markdown = "\n".join(lines)
    return {"count": len(runs), "markdown": markdown, "runs": runs}
