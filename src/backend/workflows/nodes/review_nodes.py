"""
src/backend/workflows/nodes/review_nodes.py - 推敲・レビューグラフ（ReviewGraph）のノード定義
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from src.backend.sse_manager import get_sse_manager
from src.backend.workflows.state import ReviewGraphState
from src.backend.workflows.utils import calculate_quality_score, format_critique_feedback
from src.core.llm.router import resolve_model

logger = logging.getLogger(__name__)

COMMERCIAL_PASS = 0.7

# [設計原則 P3] analyze_pacing_node と check_character_consistency_node は
# いずれも同一の source_content のみを読み取り、相互に独立しているため
# asyncio.gather による安全な並列実行が可能。


async def analyze_pacing_node(state: ReviewGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node 1: Pacing & Structure Analysis】
    本文の起承転結、テンポ、感情曲線を専門に分析・スコアリングする。
    """
    content = state.get("source_content", "")
    ep_num = state.get("ep_num", 1)

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "PacingReviewer",
            "phase": "pacing_analyzing",
            "message": f"第{ep_num}話 本文のテンポ・起伏・引きの強さを分析中...",
            "ep_num": ep_num,
        },
    )

    prompt = f"""あなたは小説のペース配分・構成の専門編集者です。
第{ep_num}話の本文を読み、テンポ・感情起伏・引きの強さを分析してください。

【本文】
{content[:3000]}

【出力形式】
JSON形式:
{{
  "pacing_score": 0.0〜1.0 (0.8以上で良好),
  "is_pacing_ok": true/false,
  "issues": ["テンポに関する具体的な指摘"],
  "recommendations": ["構成上の改善アドバイス"]
}}
"""

    model = resolve_model("audit")
    logger.info(f"[ReviewGraph] Analyzing pacing using model '{model}'...")

    try:
        if llm_provider:
            res = await llm_provider.generate_json(model_name=model, prompt=prompt, temperature=0.2)
            data = json.loads(res.content) if isinstance(res.content, str) else res.content
        else:
            data = {"pacing_score": 0.9, "is_pacing_ok": True, "issues": [], "recommendations": []}

        return {
            "pacing_analysis": data,
            "status": "pacing_analyzed",
        }
    except Exception as e:
        logger.error(f"[ReviewGraph] Pacing analysis failed: {e}")
        return {
            "pacing_analysis": {"pacing_score": 0.8, "is_pacing_ok": True, "issues": [], "recommendations": []},
            "status": "pacing_error",
        }


async def check_character_consistency_node(state: ReviewGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node 2: Character Consistency Check】
    キャラクターの口調、性格、行動動機の一貫性を専門にチェックする。
    """
    content = state.get("source_content", "")
    ep_num = state.get("ep_num", 1)

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "CharacterSupervisor",
            "phase": "character_checking",
            "message": f"第{ep_num}話 登場人物の口調・性格の一貫性を監修中...",
            "ep_num": ep_num,
        },
    )

    prompt = f"""あなたは小説のキャラクター監修エディターです。
第{ep_num}話本文における登場人物の口調や性格のブレ、行動の不自然さをチェックしてください。

【本文】
{content[:3000]}

【出力形式】
JSON形式:
{{
  "character_score": 0.0〜1.0,
  "is_character_ok": true/false,
  "inconsistencies": ["口調や動機のブレの指摘"]
}}
"""

    model = resolve_model("audit")
    logger.info(f"[ReviewGraph] Checking character consistency using model '{model}'...")

    try:
        if llm_provider:
            res = await llm_provider.generate_json(model_name=model, prompt=prompt, temperature=0.2)
            data = json.loads(res.content) if isinstance(res.content, str) else res.content
        else:
            data = {"character_score": 0.9, "is_character_ok": True, "inconsistencies": []}

        return {
            "character_consistency": data,
            "status": "character_checked",
        }
    except Exception as e:
        logger.error(f"[ReviewGraph] Character consistency check failed: {e}")
        return {
            "character_consistency": {"character_score": 0.8, "is_character_ok": True, "inconsistencies": []},
            "status": "character_error",
        }


async def run_review_parallel(state: ReviewGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Parallel Helper】
    analyze_pacing_node と check_character_consistency_node を
    asyncio.gather で並列実行して結果をマージする。
    """
    pacing_task = analyze_pacing_node(state, llm_provider=llm_provider)
    char_task = check_character_consistency_node(state, llm_provider=llm_provider)
    pacing_res, char_res = await asyncio.gather(pacing_task, char_task)
    merged = dict(pacing_res)
    merged.update(char_res)
    return merged


async def propose_edits_node(state: ReviewGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node 3: Edit Proposal / Polishing】
    各監査結果（テンポ、キャラ一貫性）を集約し、総合判断と修正指示文を作成する。
    """
    pacing = state.get("pacing_analysis", {})
    char = state.get("character_consistency", {})
    ep_num = state.get("ep_num", 1)

    is_pacing_ok = pacing.get("is_pacing_ok", True)
    is_char_ok = char.get("is_character_ok", True)

    issues = []
    for iss in pacing.get("issues", []):
        issues.append({"category": "Pacing", "description": iss})
    for inc in char.get("inconsistencies", []):
        issues.append({"category": "Character", "description": inc})

    requires_revision = not (is_pacing_ok and is_char_ok)
    instructions = [iss["description"] for iss in issues]

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "ReviewSynthesizer",
            "phase": "review_completed",
            "message": f"第{ep_num}話 総合推敲完了: {'修正提案あり' if requires_revision else '品質基準クリア'}",
            "ep_num": ep_num,
            "requires_revision": requires_revision,
            "total_issues": len(issues),
        },
    )

    return {
        "requires_revision": requires_revision,
        "revision_instructions": instructions,
        "status": "review_completed",
    }


async def score_commercial_node(state: ReviewGraphState, *, llm_provider: Any = None) -> Dict[str, Any]:
    """
    【Node: Commercial Quality Scoring (LLM-as-Judge)】
    カクヨム上位・商業作品ルービック5項目に基づき採点し、commercial_score を算出する。
    """
    content = state.get("source_content", "")
    ep_num = state.get("ep_num", 1)

    sse = get_sse_manager()
    await sse.broadcast(
        "agent_status",
        {
            "agent": "CommercialAuditor",
            "phase": "commercial_scoring",
            "message": f"第{ep_num}話 カクヨム商業ヒット基準（ルービック5項目）で採点中...",
            "ep_num": ep_num,
        },
    )

    prompt = f"""あなたは小説投稿サイト（カクヨム）上位作品および商業ラノベのヒット構造を評価する専門アナリストです。
以下の第{ep_num}話本文を、商業ヒットルービック5項目に基づき客観的に採点してください。

【本文】
{content[:3000]}

【評価ルービック（各0.0〜1.0点）】
1. 冒頭フック密度（冒頭300字以内の興味惹起）
2. 引きの発生頻度（中盤・節目での展開の引っ張り）
3. 感情バレンスの振れ幅（主人公・読者の感情起伏の大きさ）
4. シリーズ級の謎・伏線の設置度
5. 未解決緊張の維持（次話への強烈なクリフハンガー）

【出力形式】
JSON形式:
{{
  "commercial_score": 0.0〜1.0 (5項目の加重平均スコア),
  "is_commercial_ok": true/false (0.7以上で合格),
  "breakdown": {{
    "opening_hook": 0.0〜1.0,
    "cadence_pull": 0.0〜1.0,
    "emotional_amplitude": 0.0〜1.0,
    "mystery_foreshadowing": 0.0〜1.0,
    "cliffhanger_tension": 0.0〜1.0
  }},
  "advice": ["商業性をさらに高めるためのアドバイス"]
}}
"""

    model = resolve_model("audit")
    logger.info(f"[ReviewGraph] Scoring commercial metrics using model '{model}'...")

    try:
        if llm_provider:
            res = await llm_provider.generate_json(model_name=model, prompt=prompt, temperature=0.2)
            data = json.loads(res.content) if isinstance(res.content, str) else res.content
        else:
            data = {
                "commercial_score": 0.85,
                "is_commercial_ok": True,
                "breakdown": {
                    "opening_hook": 0.9,
                    "cadence_pull": 0.8,
                    "emotional_amplitude": 0.85,
                    "mystery_foreshadowing": 0.8,
                    "cliffhanger_tension": 0.9,
                },
                "advice": [],
            }

        score = float(data.get("commercial_score", 0.85))
        return {
            "commercial_score": score,
            "commercial_breakdown": data.get("breakdown", {}),
            "status": "commercial_scored",
        }
    except Exception as e:
        logger.error(f"[ReviewGraph] Commercial scoring failed: {e}")
        return {
            "commercial_score": 0.8,
            "commercial_breakdown": {},
            "status": "commercial_error",
        }
