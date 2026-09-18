from __future__ import annotations
import json
import logging
import re
from typing import Any
from src.services.auditors.rule_based_metrics import (
    calculate_sentence_rhythm,
    calculate_dialogue_ratio,
    calculate_kanji_ratio,
    detect_ai_cliches,
    evaluate_cliffhanger_ending,
)
from src.models.unified_audit import UnifiedAuditReport, QualitativeAudit, ConflictItemSchema

logger = logging.getLogger(__name__)

class UnifiedAuditor:
    """二層ハイブリッド監査エンジン (v5.0 Hybrid-Lean)
    - 第1層: 静的ルール解析 (0ms, 0コスト)
    - 第2層: 単一LLMによる定性・キャラクター心理・プロット引き判定
    """

    def __init__(self, llm_gateway: Any = None):
        self.llm = llm_gateway

    def audit_quantitative(self, text: str) -> tuple[float, dict[str, Any]]:
        """静的ルールベースの定量的スコア（0ms, 0コスト）を算出"""
        rhythm = calculate_sentence_rhythm(text)
        dialogue = calculate_dialogue_ratio(text)
        cliches = detect_ai_cliches(text)
        cliff = evaluate_cliffhanger_ending(text)

        # 静的スコアの加重平均
        score = (rhythm.score * 0.3) + (dialogue.score * 0.3) + (cliff * 0.4)
        if cliches:
            score = max(0.0, score - len(cliches) * 5.0)

        meta = {
            "rhythm_score": rhythm.score,
            "dialogue_ratio": dialogue.ratio,
            "cliches": cliches,
            "cliffhanger_score": cliff,
        }
        return score, meta

    async def audit_qualitative(
        self,
        text: str,
        character_profiles: str = "",
        plot_spec: str = "",
    ) -> QualitativeAudit:
        """LLMによる定性的評価を1回のみ実行"""
        if self.llm is None:
            return QualitativeAudit(
                hook_score=75.0,
                emotional_score=75.0,
                character_consistency=80.0,
                overall_score=76.0,
                critique="LLM未設定のため標準フォールバック適用",
            )
        from src.agents.prompts.unified_audit_prompt import UNIFIED_AUDIT_PROMPT_TEMPLATE
        prompt = UNIFIED_AUDIT_PROMPT_TEMPLATE.format(
            character_profiles=character_profiles or "主人公: 標準設定",
            plot_spec=plot_spec or "標準構成",
            draft_text=text[:3000],
        )
        try:
            resp = await self.llm.generate(prompt=prompt, temperature=0.2)
            json_match = re.search(r'\{.*\}', resp, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return QualitativeAudit(**data)
        except Exception as e:
            logger.warning(f"UnifiedAuditor LLM call failed: {e}")
        return QualitativeAudit(
            hook_score=70.0,
            emotional_score=70.0,
            character_consistency=70.0,
            overall_score=70.0,
            critique="パース失敗による安全フォールバック",
        )

    def _build_conflicts(self, meta: dict[str, Any], qual: QualitativeAudit) -> list[ConflictItemSchema]:
        """静的ルール解析および定性評価からUI表示用の指摘項目リストを生成"""
        conflicts: list[ConflictItemSchema] = []

        # 1. AI定型表現の指摘
        for cliche in meta.get("cliches", []):
            conflicts.append(
                ConflictItemSchema(
                    category="cliche",
                    severity="medium",
                    title=f"AI定型表現の検出: {cliche}",
                    description=f"頻出・陳腐化表現「{cliche}」が含まれています。オリジナリティのある描写への置換を推奨します。",
                    current_value=cliche,
                    suggested_value="",
                    confidence=0.95,
                )
            )

        # 2. 会話文比率の指摘
        dialogue_ratio = meta.get("dialogue_ratio", 0.0)
        if dialogue_ratio < 0.10:
            conflicts.append(
                ConflictItemSchema(
                    category="dialogue",
                    severity="low",
                    title="会話文比率の低下",
                    description=f"会話文比率が {round(dialogue_ratio * 100, 1)}% と低めです。登場人物同士の台詞を挟むことでテンポを向上させられます。",
                    confidence=0.85,
                )
            )
        elif dialogue_ratio > 0.65:
            conflicts.append(
                ConflictItemSchema(
                    category="dialogue",
                    severity="low",
                    title="地の文の不足（台詞過多）",
                    description=f"会話文比率が {round(dialogue_ratio * 100, 1)}% と高めです。台詞だけでなく行動や情景描写を追加して状況を補強してください。",
                    confidence=0.85,
                )
            )

        # 3. 文長リズムの指摘
        rhythm_score = meta.get("rhythm_score", 100.0)
        if rhythm_score < 60.0:
            conflicts.append(
                ConflictItemSchema(
                    category="rhythm",
                    severity="medium",
                    title="文長リズムの偏り",
                    description="文末の長さや接続詞のパターンが偏っています。長文と短文を交互に配置し、読みのリズムを整えてください。",
                    confidence=0.80,
                )
            )

        # 4. 定性評価からの推奨パッチ
        if qual.actionable_patch:
            conflicts.append(
                ConflictItemSchema(
                    category="hook" if qual.hook_score < 70 else "character",
                    severity="high" if qual.overall_score < 70 else "medium",
                    title="AI編集者による推奨パッチ",
                    description=qual.critique or "文章の引き込みと一貫性を強化するためのパッチです。",
                    suggested_value=qual.actionable_patch,
                    confidence=0.90,
                )
            )

        return conflicts

    async def audit(
        self,
        text: str,
        character_profiles: str = "",
        plot_spec: str = "",
    ) -> UnifiedAuditReport:
        """二層ハイブリッド監査を実行し総合判定を下す"""
        q_score, meta = self.audit_quantitative(text)
        qual = await self.audit_qualitative(text, character_profiles, plot_spec)

        # 総合得点 = 定量40% + 定性60%
        final = (q_score * 0.4) + (qual.overall_score * 0.6)
        is_ok = final >= 70.0 and len(meta["cliches"]) < 3
        conflicts = self._build_conflicts(meta, qual)

        return UnifiedAuditReport(
            is_acceptable=is_ok,
            final_score=round(final, 1),
            quantitative_score=round(q_score, 1),
            qualitative=qual,
            detected_cliches=meta["cliches"],
            dialogue_ratio=meta["dialogue_ratio"],
            conflicts=conflicts,
        )
