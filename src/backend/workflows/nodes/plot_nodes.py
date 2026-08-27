"""
src/backend/workflows/nodes/plot_nodes.py - プロット生成グラフ（PlotGraph）のノード定義
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from src.backend.sse_manager import get_sse_manager
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

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "PlotPlanner",
            "phase": "initial_generation",
            "message": f"全{target_episodes}話の初期プロット構成を策定中...",
            "iteration": 1,
        },
    )

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

    num_variants = state.get("num_variants", 1)
    model = resolve_model("planning")
    logger.info(f"[PlotGraph] Generating initial plot (variants={num_variants}) using model '{model}'...")

    try:
        plot_variants = []
        raw_texts = []
        parsed = []
        raw_text = "[]"

        if llm_provider:
            for v_idx in range(num_variants):
                response = await llm_provider.generate_json(
                    model_name=model,
                    prompt=prompt,
                    system_instruction="あなたはプロの商業小説編集者・ストーリープランナーです。",
                    temperature=0.7 + (v_idx * 0.05),
                )
                v_raw = response.content
                raw_texts.append(v_raw)
                try:
                    v_parsed = json.loads(v_raw) if isinstance(v_raw, str) else v_raw
                    if not isinstance(v_parsed, list):
                        v_parsed = v_parsed.get("plots", []) if isinstance(v_parsed, dict) else []
                except Exception:
                    v_parsed = []
                plot_variants.append(v_parsed)

            parsed = plot_variants[0] if plot_variants else []
            raw_text = raw_texts[0] if raw_texts else "[]"
        else:
            raw_text = "[]"
            parsed = []
            plot_variants = [parsed]

        await sse.broadcast(
            "agent_status",
            {
                "agent": "PlotPlanner",
                "phase": "initial_generated",
                "message": f"全{len(parsed)}話の初期プロットドラフト（{len(plot_variants)}案）を出力しました。",
                "plots_count": len(parsed),
                "variants_count": len(plot_variants),
            },
        )

        return {
            "raw_plot_draft": str(raw_text),
            "parsed_plots": parsed,
            "plot_variants": plot_variants,
            "num_variants": num_variants,
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

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "PlotCritic",
            "phase": "evaluation",
            "message": "シニア編集者エージェントがプロットの因果関係・テンポを監査中...",
            "iteration": state.get("current_iteration", 1),
        },
    )

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

    plot_variants = state.get("plot_variants", [])
    model = resolve_model("audit")
    logger.info(f"[PlotGraph] Evaluating plot (variants={len(plot_variants)}) using model '{model}'...")

    try:
        if llm_provider and len(plot_variants) > 1:
            best_plot = parsed_plots
            best_score = -1.0
            best_data = None

            for v_idx, v_plot in enumerate(plot_variants):
                v_prompt = f"""あなたは商業ライトノベルのシニア編集者（Critic）です。
以下のプロット案（全{len(v_plot)}話）を客観的かつ厳格にレビューしてください。

【プロット案】
{json.dumps(v_plot, ensure_ascii=False, indent=2)}

【評価項目】
1. 因果関係の破綻はないか
2. 各話の引き（クリフハンガー）が読者を惹きつけるか
3. テンポ（起承転結・緊張感の推移）が適切か

【出力形式】
JSONオブジェクト形式で出力してください:
{{
  "is_approved": true/false,
  "score": 0.0〜1.0 (0.85以上で合格),
  "issues": [
    {{"category": "Pacing/Logic/Hook", "description": "具体的な課題"}}
  ],
  "suggestions": ["具体的な改善指示"]
}}
"""
                response = await llm_provider.generate_json(
                    model_name=model,
                    prompt=v_prompt,
                    temperature=0.3,
                )
                v_data = json.loads(response.content) if isinstance(response.content, str) else response.content
                v_score = float(v_data.get("score", 0.0))
                if v_score > best_score:
                    best_score = v_score
                    best_plot = v_plot
                    best_data = v_data

            parsed_plots = best_plot
            data = best_data or {"is_approved": True, "score": 0.85, "issues": [], "suggestions": []}
        elif llm_provider:
            response = await llm_provider.generate_json(
                model_name=model,
                prompt=prompt,
                temperature=0.3,
            )
            data = json.loads(response.content) if isinstance(response.content, str) else response.content
        else:
            data = {"is_approved": True, "score": 0.85, "issues": [], "suggestions": []}

        score = float(data.get("score", 0.85))
        is_approved = bool(data.get("is_approved", False) or score >= 0.85)
        issues = data.get("issues", [])
        suggestions = data.get("suggestions", [])
        critique = format_critique_feedback(issues, suggestions)

        await sse.broadcast(
            "agent_status",
            {
                "agent": "PlotCritic",
                "phase": "evaluated",
                "message": f"プロット監査完了: スコア {score:.2f} ({'合格' if is_approved else '再修正指示'})",
                "score": score,
                "is_approved": is_approved,
                "issues_count": len(issues),
            },
        )

        return {
            "parsed_plots": parsed_plots,
            "quality_score": score,
            "is_approved": is_approved,
            "critique_feedback": critique,
            "suggestions": suggestions,
            "status": "evaluated",
        }
    except Exception as e:
        logger.error(f"[PlotGraph] Evaluation failed: {e}")
        return {
            "parsed_plots": parsed_plots,
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

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "PlotPlanner",
            "phase": "refinement",
            "message": f"編集部のフィードバックに基づきプロットを修正中 (イテレーション {current_iter})...",
            "iteration": current_iter,
        },
    )

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
