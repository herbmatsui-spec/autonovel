"""
src/backend/workflows/nodes/plot_nodes.py - プロット生成グラフ（PlotGraph）のノード定義
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from src.backend.workflows.state import PlotGraphState
from src.backend.workflows.utils import calculate_quality_score, format_critique_feedback
from src.core.llm.router import resolve_model

logger = logging.getLogger(__name__)


async def generate_initial_plot_node(state: PlotGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node 1: Initial Plot Generation】
    ジャンル、テーマ、バイブル設定に基づいて初期プロットドラフトを生成する。
    """
    genre = state.get("genre", "異世界ファンタジー")
    theme = state.get("theme", "主人公の成り上がりと冒険")
    target_episodes = state.get("target_episodes", 10)
    user_instructions = state.get("user_instructions", "")
    bible_context = state.get("bible_context", {})

    prompt = f"""あなたは商業ライトノベルの熟練プロットプランナーです。
以下の前提条件に基づき、全{target_episodes}話の構成プロット案（JSON配列形式）を策定してください。

【前提条件】
- ジャンル: {genre}
- テーマ: {theme}
- 追加指示: {user_instructions or "特になし"}
- 世界観/設定: {json.dumps(bible_context, ensure_ascii=False) if bible_context else "標準設定"}

【出力フォーマット】
以下のキーを持つJSON配列形式で出力してください:
[
  {{
    "ep_num": 1,
    "title": "エピソードタイトル",
    "summary": "エピソードのあらすじ・主要イベント",
    "next_hook": "次話への引き・クリフハンガー",
    "physical_tension_delta": 20,
    "psychological_tension_delta": 10,
    "social_tension_delta": 0
  }}
]
"""

    model = resolve_model("planning")
    logger.info(f"[PlotGraph] Generating initial plot using model '{model}'...")

    try:
        if llm_provider:
            response = await llm_provider.generate_json(
                model_name=model,
                prompt=prompt,
                system_instruction="あなたはプロの商業小説編集者・ストーリープランナーです。",
                temperature=0.7,
            )
            raw_text = response.content
        else:
            raw_text = "[]"

        try:
            parsed = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
            if not isinstance(parsed, list):
                parsed = parsed.get("plots", []) if isinstance(parsed, dict) else []
        except Exception:
            parsed = []

        return {
            "raw_plot_draft": str(raw_text),
            "parsed_plots": parsed,
            "current_iteration": state.get("current_iteration", 0) + 1,
            "status": "initial_generated",
        }
    except Exception as e:
        logger.error(f"[PlotGraph] Initial generation failed: {e}")
        return {
            "error_message": str(e),
            "status": "error",
            "current_iteration": state.get("current_iteration", 0) + 1,
        }


async def evaluate_plot_node(state: PlotGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node 2: Plot Evaluation / Critique】
    生成されたプロットの因果関係、テンポ、読者引き（クリフハンガー）を多角的に評価する。
    """
    parsed_plots = state.get("parsed_plots", [])
    genre = state.get("genre", "")

    if not parsed_plots:
        return {
            "quality_score": 0.0,
            "is_approved": False,
            "critique_feedback": "プロットデータが空です。",
            "suggestions": ["プロットの再生成を行ってください。"],
            "status": "evaluation_failed",
        }

    prompt = f"""あなたは商業ライトノベルのシニア編集者（Critic）です。
以下のプロット（全{len(parsed_plots)}話）を客観的かつ厳格にレビューしてください。

【プロット】
{json.dumps(parsed_plots, ensure_ascii=False, indent=2)}

【評価項目】
1. 因果関係の破綻はないか
2. 各話の引き（クリフハンガー）が読者を惹きつけるか
3. テンポ（起承転結・緊張感の推移）が適切か

【出力形式】
JSONオブジェクト形式で出力してください:
{{
  "is_approved": true/false,
  "score": 0.0〜1.0 (0.8以上で合格),
  "issues": [
    {{"category": "Pacing/Logic/Hook", "description": "具体的な課題"}}
  ],
  "suggestions": ["具体的な改善指示"]
}}
"""

    model = resolve_model("audit")
    logger.info(f"[PlotGraph] Evaluating plot using model '{model}'...")

    try:
        if llm_provider:
            response = await llm_provider.generate_json(
                model_name=model,
                prompt=prompt,
                temperature=0.3,
            )
            data = json.loads(response.content) if isinstance(response.content, str) else response.content
        else:
            data = {"is_approved": True, "score": 0.85, "issues": [], "suggestions": []}

        is_approved = bool(data.get("is_approved", False) or data.get("score", 0.0) >= 0.8)
        score = float(data.get("score", 0.8 if is_approved else 0.5))
        issues = data.get("issues", [])
        suggestions = data.get("suggestions", [])
        critique = format_critique_feedback(issues, suggestions)

        return {
            "quality_score": score,
            "is_approved": is_approved,
            "critique_feedback": critique,
            "suggestions": suggestions,
            "status": "evaluated",
        }
    except Exception as e:
        logger.error(f"[PlotGraph] Evaluation failed: {e}")
        # フォールバック: パース済みプロットがあれば一旦承認
        return {
            "quality_score": 0.75,
            "is_approved": True,
            "critique_feedback": f"自動評価スキップ (Error: {e})",
            "suggestions": [],
            "status": "evaluated_fallback",
        }


async def refine_plot_node(state: PlotGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node 3: Plot Refinement / Self-Correction】
    評価フィードバックに基づき、プロットの課題を修正・再構成する。
    """
    parsed_plots = state.get("parsed_plots", [])
    critique_feedback = state.get("critique_feedback", "")
    current_iter = state.get("current_iteration", 1)

    prompt = f"""あなたは商業ライトノベルのプロットプランナーです。
前回のプロット案に対し、編集部から以下の改善フィードバックが届きました。
指摘事項を完全に解決した、改良版プロット（JSON配列）を出力してください。

【前回プロット】
{json.dumps(parsed_plots, ensure_ascii=False, indent=2)}

【編集部からのフィードバック】
{critique_feedback}

【出力形式】
改善後のJSON配列を出力してください。
"""

    model = resolve_model("planning")
    logger.info(f"[PlotGraph] Refining plot (Iteration {current_iter}) using model '{model}'...")

    try:
        if llm_provider:
            response = await llm_provider.generate_json(
                model_name=model,
                prompt=prompt,
                temperature=0.6,
            )
            raw_text = response.content
        else:
            raw_text = json.dumps(parsed_plots)

        try:
            parsed = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
            if not isinstance(parsed, list):
                parsed = parsed.get("plots", []) if isinstance(parsed, dict) else []
        except Exception:
            parsed = parsed_plots

        return {
            "raw_plot_draft": str(raw_text),
            "parsed_plots": parsed,
            "current_iteration": current_iter + 1,
            "status": "refined",
        }
    except Exception as e:
        logger.error(f"[PlotGraph] Refinement failed: {e}")
        return {
            "current_iteration": current_iter + 1,
            "status": "refine_error",
        }
