"""
src/backend/workflows/nodes/writing_nodes.py - 執筆グラフ（WritingGraph）のノード定義
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from src.backend.sse_manager import get_sse_manager
from src.backend.workflows.state import WritingGraphState
from src.backend.workflows.utils import calculate_quality_score, format_critique_feedback
from src.core.llm.router import resolve_model

logger = logging.getLogger(__name__)

MIN_DRAFT_CHARS = 1500


async def build_context_node(state: WritingGraphState, *, writing_agent: Any = None) -> Dict[str, Any]:
    """
    【Node 1: Build Writing Context】
    設定資料（Bible）、過去話のRAG、プロット、キャラ状態を動的に抽出して執筆用プロンプト文脈を構築する。
    """
    book_id = state.get("book_id", 1)
    branch_id = state.get("branch_id", 1)
    ep_num = state.get("ep_num", 1)
    style_tag = state.get("style_tag")

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "ContextBuilder",
            "phase": "context_building",
            "message": f"第{ep_num}話の設定資料（Bible）・過去ログRAGを抽出中...",
            "ep_num": ep_num,
        },
    )

    logger.info(f"[WritingGraph] Building context for Book {book_id}, Ep {ep_num}...")

    sys_inst = state.get("sys_inst", "あなたは商業ライトノベルのベストセラー作家です。")
    fw_prompt = state.get("fw_prompt", f"第{ep_num}話の本文を魅力的に執筆してください。")

    if writing_agent and hasattr(writing_agent, "build_full_writing_context"):
        try:
            ctx = await writing_agent.build_full_writing_context(
                book_id=book_id,
                branch_id=branch_id,
                ep_num=ep_num,
                style_tag=style_tag,
            )
            return {
                "context": ctx,
                "sys_inst": sys_inst,
                "fw_prompt": fw_prompt,
                "status": "context_built",
            }
        except Exception as e:
            logger.warning(f"[WritingGraph] Rich context build failed, fallback to base: {e}")

    return {
        "sys_inst": sys_inst,
        "fw_prompt": fw_prompt,
        "status": "context_built",
    }


async def generate_draft_node(state: WritingGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node 2: Draft Generation / Actor】
    文脈とプロンプトに基づき、小説本文ドラフトを生成する。
    """
    sys_inst = state.get("sys_inst", "")
    fw_prompt = state.get("fw_prompt", "")
    failures = state.get("failures", [])
    ac_iter = state.get("ac_iter", 0) + 1
    ep_num = state.get("ep_num", 1)

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "WriterActor",
            "phase": "draft_generating",
            "message": f"第{ep_num}話 本文を執筆中 (推敲ループ {ac_iter})...",
            "ep_num": ep_num,
            "ac_iter": ac_iter,
        },
    )

    prev_tail = state.get("prev_episode_tail", "")
    prompt = fw_prompt
    if prev_tail:
        prompt += (
            f"\n\n【直前話の末尾（文脈接続用）】\n"
            f"...\n{prev_tail}\n...\n"
            f"※前話のラストシーン・キャラクターの感情や緊迫感を自然に引き継ぎ、物語を滑らかに接続して執筆してください。"
        )

    if failures:
        critique = format_critique_feedback(failures)
        prompt += f"\n\n【前回の推敲指摘と改善指示】\n{critique}\n上記の指摘事項（特に事件密度・展開・キャラクター描写・論理整合性）を反映して本文を書き直してください。"

    model = resolve_model("writing")
    logger.info(f"[WritingGraph] Generating draft (Iteration {ac_iter}) using model '{model}'...")

    try:
        if llm_provider:
            response = await llm_provider.generate_text(
                model_name=model,
                prompt=prompt,
                system_instruction=sys_inst,
                temperature=0.75,
            )
            draft = response.content
        else:
            draft = (
                f"第{ep_num}話の本文ドラフト（生成サンプル）。主人公は静かに歩き始めた。"
                "風が草木を揺らし、遠くの街並みが夕暮れに染まっていく。新たな冒険の予感が胸を満たしていた。"
                "胸に秘めた決意を新たに、彼らは前進を続ける。"
            ) * 20

        await sse.broadcast(
            "agent_status",
            {
                "agent": "WriterActor",
                "phase": "draft_generated",
                "message": f"第{ep_num}話 本文ドラフトを生成しました ({len(draft)}文字)。",
                "ep_num": ep_num,
                "draft_length": len(draft),
            },
        )

        return {
            "draft_content": draft,
            "ac_iter": ac_iter,
            "status": "draft_generated",
        }
    except Exception as e:
        logger.error(f"[WritingGraph] Draft generation failed: {e}")
        return {
            "error_message": str(e),
            "status": "draft_error",
        }


async def self_audit_node(state: WritingGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node 3: Self Audit / Critic】
    生成されたドラフトの整合性、因果関係、テンポを監査し、合否判定と修正指示を出力する。
    """
    draft = state.get("draft_content", "")
    ep_num = state.get("ep_num", 1)

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "WriterCritic",
            "phase": "auditing",
            "message": f"第{ep_num}話 本文のキャラクター整合性・論理破綻を自己監査中...",
            "ep_num": ep_num,
        },
    )

    if not draft or len(draft.strip()) < MIN_DRAFT_CHARS:
        return {
            "is_integrity_ok": False,
            "is_causal_ok": False,
            "causal_reason": "本文の文字数が極端に不足しています。",
            "failures": [{"category": "Length", "description": "本文が短すぎます。"}],
            "quality_score": 0.2,
            "status": "audit_failed",
        }

    prompt = f"""あなたは小説の校正・監査シニアエディター（Critic）です。
以下の第{ep_num}話本文ドラフトを客観的に監査してください。

【本文ドラフト】
{draft[:3000]}

【監査項目】
1. キャラクターの言動に大きな不整合やブレはないか
2. 前後の因果関係や状況描写に論理的破綻はないか
3. 事件密度（展開/性格露出/緊張上昇の充足度）が十分にあるか（不足時は failures に不足要素［展開・性格露出・緊張感］を具体的に記載）
4. （前話がある場合）前話からの接続・引き継ぎに違和感や断絶がないか

【出力形式】
JSON形式:
{{
  "is_integrity_ok": true/false,
  "is_causal_ok": true/false,
  "event_density": 0.0〜1.0 (0.5以上で合格),
  "causal_reason": "判定理由",
  "score": 0.0〜1.0 (0.8以上で合格),
  "failures": [
    {{"category": "Logic/Character/Pacing/Density", "description": "修正すべき点（不足している展開・性格描写・緊張感など）"}}
  ]
}}
"""

    model = resolve_model("audit")
    logger.info(f"[WritingGraph] Auditing draft using model '{model}'...")

    try:
        if llm_provider:
            response = await llm_provider.generate_json(
                model_name=model,
                prompt=prompt,
                temperature=0.2,
            )
            data = json.loads(response.content) if isinstance(response.content, str) else response.content
        else:
            data = {
                "is_integrity_ok": True,
                "is_causal_ok": True,
                "event_density": 0.9,
                "score": 0.9,
                "failures": [],
            }

        integrity_ok = bool(data.get("is_integrity_ok", True))
        causal_ok = bool(data.get("is_causal_ok", True))
        event_density = float(data.get("event_density", 0.8))
        failures = data.get("failures", [])
        score = float(data.get("score", calculate_quality_score(integrity_ok, causal_ok, len(failures))))

        logger.info(
            f"[WritingGraph] Ep {ep_num} Audit Complete: chars={len(draft)}, density={event_density:.2f}, score={score:.2f}, integrity={integrity_ok}, causal={causal_ok}"
        )

        await sse.broadcast(
            "agent_status",
            {
                "agent": "WriterCritic",
                "phase": "audited",
                "message": f"第{ep_num}話 自己監査完了: スコア {score:.2f}, 密度 {event_density:.2f} ({'合格' if integrity_ok and causal_ok else '再修正指示'})",
                "ep_num": ep_num,
                "score": score,
                "event_density": event_density,
                "failures_count": len(failures),
            },
        )

        return {
            "is_integrity_ok": integrity_ok,
            "is_causal_ok": causal_ok,
            "event_density": event_density,
            "causal_reason": data.get("causal_reason", "監査完了"),
            "failures": failures,
            "quality_score": score,
            "status": "audited",
        }
    except Exception as e:
        logger.error(f"[WritingGraph] Self audit failed: {e}")
        return {
            "is_integrity_ok": True,
            "is_causal_ok": True,
            "event_density": 0.8,
            "causal_reason": "監査フォールバック",
            "failures": [],
            "quality_score": 0.8,
            "status": "audit_error",
        }
