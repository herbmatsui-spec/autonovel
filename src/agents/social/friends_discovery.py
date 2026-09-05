"""Friends Discovery: Infer and create related character candidates (Step 47)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiscoveredCharacterCandidate(BaseModel):
    """Profile of a newly discovered related character."""

    name: str = Field(description="Generated character name")
    relation_to_base_char: str = Field(description="Relationship to the seed character")
    role: str = Field(description="Narrative role (ally, rival, mentor, informant, nemesis)")
    archetype: str = Field(description="Character archetype")
    personality: str = Field(description="Personality summary and speech traits")
    conflict_potential: str = Field(description="Potential for conflict or plot friction")


# ルールベースフォールバック用テンプレート
ROLE_INFERENCE_TEMPLATES = [
    {
        "pattern": ["勇者", "剣士", "主人公", "騎士"],
        "candidates": [
            {
                "name": "エレナ・アルスター",
                "relation": "かつての同門であり、異なる信念で剣を振るう好敵手",
                "role": "rival",
                "archetype": "高潔な宿敵",
                "personality": "冷静沈着。礼節を重んじるが主人公の甘さを厳しく糾弾する。",
                "conflict_potential": "王国の正義と個人の救済の優先順位を巡る思想対立。",
            },
            {
                "name": "ヴィクトル・黒鉄",
                "relation": "幼少期に剣の基礎を教え込んだ無頼の元傭兵師匠",
                "role": "mentor",
                "archetype": "老練の隠者",
                "personality": "皮肉屋で酒好き。命のやり取りの本質を冷徹に見抜く。",
                "conflict_potential": "過去の誓いと未解決の因縁による主人公への試練。",
            },
        ],
    },
    {
        "pattern": ["魔導師", "賢者", "魔法使い", "魔王", "研究者"],
        "candidates": [
            {
                "name": "サイラス・ファントム",
                "relation": "禁忌魔導書を共に研究した末に袂を分かった元親友",
                "role": "nemesis",
                "archetype": "冷徹な知性派敵役",
                "personality": "探求心に狂気を宿す。目的のために犠牲を厭わない合理主義者。",
                "conflict_potential": "禁断の魔法技術の解放を巡る倫理的対立。",
            },
            {
                "name": "シャロン・ミスト",
                "relation": "地下市場に精通する魔導具情報屋",
                "role": "informant",
                "archetype": "抜け目のない取引人",
                "personality": "金と情報に忠実だが、情に脆い一面を持つ。",
                "conflict_potential": "情報の二重売却によるパーティの危機。",
            },
        ],
    },
]


def discover_related_characters(
    base_character: dict[str, Any],
    world_context: str = "",
    llm: Any = None,
    count: int = 2,
) -> list[DiscoveredCharacterCandidate]:
    """Discover unintroduced related characters based on seed character traits."""
    char_name = base_character.get("name", "主人公")
    role_or_desc = str(base_character.get("role") or base_character.get("description") or "")

    # 1. LLM 呼び出し試行
    if llm:
        try:
            prompt = f"""
あなたはファンタジー小説のキャラクター関係性設計の専門家です。
以下のキャラクターの人間関係を拡張するため、物語の葛藤やドラマを生み出す「未登場の関連キャラクター」を{count}名提案してください。

【基準キャラクター】
名前: {char_name}
役割・特徴: {role_or_desc}
世界観補足: {world_context}

以下のJSON配列形式のみで返答してください:
[
  {{
    "name": "キャラクター名",
    "relation_to_base_char": "{char_name}との具体的関係（例: 師匠の宿敵）",
    "role": "物語上の役割",
    "archetype": "性格アーキタイプ",
    "personality": "性格・口調の特徴",
    "conflict_potential": "物語で生じるドラマ・対立ポテンシャル"
  }}
]
"""
            resp = llm.generate(prompt) if hasattr(llm, "generate") else str(llm(prompt))
            match = re.search(r"\[.*\]", resp, re.DOTALL)
            if match:
                raw_list = json.loads(match.group(0))
                candidates = [DiscoveredCharacterCandidate(**item) for item in raw_list[:count]]
                if candidates:
                    return candidates
        except Exception as e:
            logger.warning(f"LLM friends discovery failed, using rule-based fallback: {e}")

    # 2. ルールベースフォールバック
    matched_candidates = []
    combined_text = f"{char_name} {role_or_desc}"

    for tpl in ROLE_INFERENCE_TEMPLATES:
        if any(p in combined_text for p in tpl["pattern"]):
            for c in tpl["candidates"]:
                matched_candidates.append(DiscoveredCharacterCandidate(
                    name=c["name"],
                    relation_to_base_char=f"{char_name}の{c['relation']}",
                    role=c["role"],
                    archetype=c["archetype"],
                    personality=c["personality"],
                    conflict_potential=c["conflict_potential"],
                ))

    # パターンにヒットしない場合の一般フォールバック
    if not matched_candidates:
        matched_candidates.append(DiscoveredCharacterCandidate(
            name=f"{char_name}の旧友・ローガン",
            relation_to_base_char=f"{char_name}が少年時代を共に過ごした幼馴染",
            role="ally",
            archetype="忠実な戦友",
            personality="豪快で実直。主人公を常に背中から支える。",
            conflict_potential="主人公の変化に対する戸惑いと忠誠心の揺らぎ。",
        ))
        matched_candidates.append(DiscoveredCharacterCandidate(
            name=f"暗影の密偵・シャドウ",
            relation_to_base_char=f"{char_name}を影から監視する謎の諜報員",
            role="informant",
            archetype="謎めいた傍観者",
            personality="寡黙で神出鬼没。真意を決して見せない。",
            conflict_potential="敵か味方か測れない情報提供による疑心暗鬼。",
        ))

    return matched_candidates[:count]


__all__ = ["DiscoveredCharacterCandidate", "discover_related_characters"]
