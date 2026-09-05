"""Layer 4: Scene-Aware Dynamic Trimming (Step 30)."""
from __future__ import annotations

import logging
from typing import Any, List, Dict

from src.services.compression.models import (
    AbstractionLayerOutput,
    TrimmedContextOutput,
    SceneType,
)
from src.services.compression.layer1_keywords import count_tokens

logger = logging.getLogger(__name__)

SCENE_CATEGORY_WEIGHTS: dict[SceneType, dict[str, float]] = {
    "combat": {
        "武術・スキル": 2.2,
        "主要キャラ": 1.6,
        "アイテム・装備": 1.5,
        "核心設定": 1.2,
        "伏線": 1.0,
        "地理・勢力": 0.4,
    },
    "daily": {
        "主要キャラ": 2.0,
        "地理・勢力": 1.3,
        "アイテム・装備": 1.1,
        "伏線": 0.8,
        "核心設定": 0.7,
        "武術・スキル": 0.3,
    },
    "psychological": {
        "主要キャラ": 2.0,
        "伏線": 1.9,
        "核心設定": 1.3,
        "地理・勢力": 0.8,
        "アイテム・装備": 0.7,
        "武術・スキル": 0.4,
    },
    "political": {
        "地理・勢力": 2.2,
        "伏線": 1.9,
        "主要キャラ": 1.6,
        "核心設定": 1.4,
        "アイテム・装備": 0.8,
        "武術・スキル": 0.4,
    },
    "general": {
        "主要キャラ": 1.8,
        "核心設定": 1.6,
        "伏線": 1.5,
        "武術・スキル": 1.1,
        "地理・勢力": 1.0,
        "アイテム・装備": 0.9,
    },
}


class Layer4SceneTrimmer:
    """Trims facts dynamically according to scene intent and token budget."""

    def __init__(
        self,
        max_tokens: int = 1500,
        preserve_categories: list[str] | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.preserve_categories = preserve_categories or ["主要キャラ", "核心設定", "伏線"]

    def detect_scene_type(self, plot_summary: str, scenes: list[str] | None = None) -> SceneType:
        """Infer scene narrative type from plot summary and scenes."""
        combined = f"{plot_summary} {' '.join(scenes or [])}".lower()
        if any(w in combined for w in ["戦闘", "決闘", "討伐", "撃破", "襲撃", "激突", "交戦", "斬", "剣", "魔王"]):
            return "combat"
        elif any(w in combined for w in ["会議", "議会", "政略", "関税", "条約", "宣戦", "同盟", "陰謀", "外交"]):
            return "political"
        elif any(w in combined for w in ["心理", "葛藤", "苦悩", "トラウマ", "独白", "疑念", "迷い"]):
            return "psychological"
        elif any(w in combined for w in ["日常", "宴", "酒場", "休息", "街歩き", "料理", "雑談"]):
            return "daily"
        return "general"

    def trim(
        self,
        abstraction_output: AbstractionLayerOutput,
        scene_type: SceneType = "general",
        max_tokens: int | None = None,
        keywords: list[str] | None = None,
        original_token_count: int = 0,
    ) -> TrimmedContextOutput:
        """Trim facts down to token budget based on scene type importance."""
        budget = max_tokens or self.max_tokens
        weights = SCENE_CATEGORY_WEIGHTS.get(scene_type, SCENE_CATEGORY_WEIGHTS["general"])
        kws = [k.lower() for k in (keywords or [])]

        all_scored_facts = []
        for cat, facts in abstraction_output.categorized_facts.items():
            cat_weight = weights.get(cat, 1.0)
            for fact_item in facts:
                content = fact_item.get("fact", "")
                entity = fact_item.get("entity", "")
                
                # キーワード一致ボーナス
                kw_bonus = 1.0
                if any(k in content.lower() or k in entity.lower() for k in kws):
                    kw_bonus = 1.4

                score = cat_weight * kw_bonus
                is_mandatory = cat in self.preserve_categories

                all_scored_facts.append({
                    "category": cat,
                    "content": content,
                    "entity": entity,
                    "score": round(score, 3),
                    "mandatory": is_mandatory,
                    "tokens": count_tokens(content),
                })

        # 優先度順にソート（必須項目優先、次にスコア降順）
        all_scored_facts.sort(key=lambda x: (x["mandatory"], x["score"]), reverse=True)

        selected_facts = []
        retained_entities = set()
        current_tokens = 0

        # まず必須カテゴリからトークン制限内で採用
        for f in all_scored_facts:
            f_tokens = f["tokens"]
            if current_tokens + f_tokens <= budget:
                selected_facts.append(f)
                current_tokens += f_tokens
                if f["entity"]:
                    retained_entities.add(f["entity"])
            else:
                # 予算超過した事実はスキップし、後続の小さい事実を引き続き探索
                continue

        # 自然なMarkdownテキスト整形
        concepts = list(abstraction_output.abstract_concepts)
        formatted_text = self._format_markdown(selected_facts, concepts)
        final_tokens = count_tokens(formatted_text)

        # 厳密な予算超過防止: マークダウン装飾・ヘッダーで超過した場合、下位事実から順に削る
        while final_tokens > budget and selected_facts:
            removed = selected_facts.pop()
            if removed.get("entity") in retained_entities:
                retained_entities.discard(removed["entity"])
            formatted_text = self._format_markdown(selected_facts, concepts)
            final_tokens = count_tokens(formatted_text)

        while final_tokens > budget and concepts:
            concepts.pop()
            formatted_text = self._format_markdown(selected_facts, concepts)
            final_tokens = count_tokens(formatted_text)

        # 削減率計算
        reduction = 0.0
        if original_token_count > 0:
            reduction = max(0.0, 1.0 - (final_tokens / original_token_count))

        return TrimmedContextOutput(
            compressed_text=formatted_text,
            token_count=final_tokens,
            retained_entities=sorted(list(retained_entities)),
            reduction_ratio=round(reduction, 3),
            scene_type=scene_type,
        )

    def _format_markdown(self, facts: list[dict[str, Any]], concepts: list[str]) -> str:
        """Format selected facts into structured Markdown sections."""
        if not facts and not concepts:
            return ""

        by_cat: dict[str, list[str]] = {}
        for f in facts:
            by_cat.setdefault(f["category"], []).append(f["content"])

        sections = []
        if concepts:
            sections.append(f"【シーン主要概念】\n- {' / '.join(concepts[:8])}")

        for cat, contents in by_cat.items():
            fact_lines = "\n".join(f"- {c}" for c in contents)
            sections.append(f"【{cat}】\n{fact_lines}")

        return "\n\n".join(sections).strip()


__all__ = ["Layer4SceneTrimmer", "SCENE_CATEGORY_WEIGHTS"]
