"""Layer 4: Scene-Aware Dynamic Trimming (Step 30)."""
from __future__ import annotations

import logging
import math
from typing import Any, List, Dict, Tuple

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

# キーワード重み付け辞書（シーンタイプ検出用）
SCENE_KEYWORDS_WEIGHTED: dict[SceneType, dict[str, float]] = {
    "combat": {
        "戦闘": 1.0, "決闘": 1.0, "討伐": 1.0, "撃破": 1.0, "襲撃": 1.0,
        "激突": 0.9, "交戦": 0.9, "斬": 0.8, "剣": 0.7, "魔王": 0.9,
        "抜刀": 0.8, "迅雷": 0.7, "武術": 0.6, "必殺": 0.8, "一撃": 0.7,
    },
    "daily": {
        "日常": 1.0, "宴": 0.9, "酒場": 0.9, "休息": 0.9, "街歩き": 0.8,
        "料理": 0.7, "雑談": 0.8, "市場": 0.7, "買い物": 0.7, "会話": 0.6,
        "食事": 0.7, "睡眠": 0.6, "朝": 0.5, "夜": 0.5, "穏やか": 0.6,
    },
    "psychological": {
        "心理": 1.0, "葛藤": 1.0, "苦悩": 0.9, "トラウマ": 0.9, "独白": 0.9,
        "疑念": 0.8, "迷い": 0.8, "回想": 0.8, "記憶": 0.7, "内面": 0.8,
        "不安": 0.7, "恐怖": 0.7, "後悔": 0.7, "決意": 0.6, "覚悟": 0.7,
    },
    "political": {
        "会議": 1.0, "議会": 1.0, "政略": 1.0, "関税": 0.9, "条約": 0.9,
        "宣戦": 0.9, "同盟": 0.9, "陰謀": 0.9, "外交": 0.8, "交渉": 0.8,
        "宰相": 0.8, "ギルド": 0.7, "領地": 0.7, "同盟": 0.8, "謀略": 0.9,
    },
}


def _softmax(scores: Dict[str, float]) -> Dict[str, float]:
    """Apply softmax to normalize scores to probabilities."""
    if not scores:
        return {}
    max_score = max(scores.values())
    exp_scores = {k: math.exp(v - max_score) for k, v in scores.items()}
    sum_exp = sum(exp_scores.values())
    return {k: v / sum_exp for k, v in exp_scores.items()}


def _blend_category_weights(
    scene_weights: Dict[SceneType, float],
) -> Dict[str, float]:
    """Blend category weights from multiple scene types based on their confidence scores."""
    blended: Dict[str, float] = {}
    for scene_type, weight in scene_weights.items():
        if weight <= 0:
            continue
        cat_weights = SCENE_CATEGORY_WEIGHTS.get(scene_type, SCENE_CATEGORY_WEIGHTS["general"])
        for cat, cat_weight in cat_weights.items():
            blended[cat] = blended.get(cat, 0.0) + cat_weight * weight
    return blended


class Layer4SceneTrimmer:
    """Trims facts dynamically according to scene intent and token budget."""

    def __init__(
        self,
        max_tokens: int = 1500,
        preserve_categories: list[str] | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.preserve_categories = preserve_categories or ["主要キャラ", "核心設定", "伏線"]

    def detect_scene_type(
        self, plot_summary: str, scenes: list[str] | None = None
    ) -> SceneType:
        """Infer scene narrative type from plot summary and scenes (legacy single-label)."""
        multi = self.detect_scene_type_multi(plot_summary, scenes)
        return multi[0][0] if multi else "general"

    def detect_scene_type_multi(
        self, plot_summary: str, scenes: list[str] | None = None
    ) -> List[Tuple[SceneType, float]]:
        """Infer scene narrative type with confidence scores (multi-label)."""
        combined = f"{plot_summary} {' '.join(scenes or [])}".lower()
        
        scores = {}
        for scene_type, keywords in SCENE_KEYWORDS_WEIGHTED.items():
            score = 0.0
            for kw, kw_weight in keywords.items():
                if kw in combined:
                    score += kw_weight
            if score > 0:
                scores[scene_type] = score
        
        if not scores:
            return [("general", 1.0)]
        
        # Apply softmax to get confidence scores
        probs = _softmax(scores)
        # Sort by confidence descending
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        return sorted_probs

    def trim(
        self,
        abstraction_output: AbstractionLayerOutput,
        scene_type: SceneType = "general",
        max_tokens: int | None = None,
        keywords: list[str] | None = None,
        original_token_count: int = 0,
        scene_weights: Dict[SceneType, float] | None = None,
    ) -> TrimmedContextOutput:
        """Trim facts down to token budget based on scene type importance.
        
        Args:
            abstraction_output: Output from Layer 3
            scene_type: Single scene type (legacy, used if scene_weights not provided)
            max_tokens: Token budget override
            keywords: Keywords for bonus scoring
            original_token_count: Original token count for reduction calculation
            scene_weights: Dict of scene_type -> confidence weight for multi-label blending
        """
        budget = max_tokens or self.max_tokens
        kws = [k.lower() for k in (keywords or [])]

        # Determine category weights: use blended weights if scene_weights provided
        if scene_weights:
            weights = _blend_category_weights(scene_weights)
            # Determine primary scene type for output metadata
            primary_scene = max(scene_weights.items(), key=lambda x: x[1])[0] if scene_weights else scene_type
        else:
            weights = SCENE_CATEGORY_WEIGHTS.get(scene_type, SCENE_CATEGORY_WEIGHTS["general"])
            primary_scene = scene_type

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
            scene_type=primary_scene,
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


__all__ = [
    "Layer4SceneTrimmer",
    "SCENE_CATEGORY_WEIGHTS",
    "SCENE_KEYWORDS_WEIGHTED",
    "_softmax",
    "_blend_category_weights",
]
