"""Scene type accuracy test annotations."""
from __future__ import annotations

from typing import Dict, List, Any

# Ground truth annotations for each scene type
# These define what categories/entities MUST be preserved for each scene type

SCENE_ANNOTATIONS: Dict[str, Dict[str, Any]] = {
    "combat": {
        "description": "Combat/battle scenes - focus on action, skills, weapons",
        "required_categories": ["武術・スキル", "主要キャラ", "アイテム・装備"],
        "optional_categories": ["核心設定", "伏線"],
        "excluded_categories": ["地理・勢力", "日常"],
        "required_entities": ["アルカディア", "ヴォルケイン", "エクスカリバー", "迅雷"],
        "min_category_preservation_rate": 0.9,  # 90% of required categories must appear
        "min_entity_retention_rate": 0.85,      # 85% of key entities must be retained
    },
    "daily": {
        "description": "Daily life/slice of life scenes - focus on characters, relationships, setting",
        "required_categories": ["主要キャラ", "地理・勢力", "アイテム・装備"],
        "optional_categories": ["伏線", "核心設定"],
        "excluded_categories": ["武術・スキル"],
        "required_entities": ["アルカディア", "カロル", "王都グランヴァル", "冒険者ギルド", "治癒のポーション"],
        "min_category_preservation_rate": 0.9,
        "min_entity_retention_rate": 0.85,
    },
    "psychological": {
        "description": "Psychological/internal conflict scenes - focus on characters, foreshadowing, core lore",
        "required_categories": ["主要キャラ", "伏線", "核心設定"],
        "optional_categories": ["地理・勢力", "アイテム・装備"],
        "excluded_categories": ["武術・スキル"],
        "required_entities": ["アルカディア", "ガレス", "ヴォルケイン", "エクスカリバー", "迅雷"],
        "min_category_preservation_rate": 0.9,
        "min_entity_retention_rate": 0.85,
    },
    "political": {
        "description": "Political/intrigue scenes - focus on factions, geography, foreshadowing",
        "required_categories": ["地理・勢力", "伏線", "主要キャラ", "核心設定"],
        "optional_categories": ["アイテム・装備"],
        "excluded_categories": ["武術・スキル"],
        "required_entities": ["バルガス", "ミレナ", "商人ギルド", "辺境警備隊", "エルシオン協定", "関税"],
        "min_category_preservation_rate": 0.85,
        "min_entity_retention_rate": 0.8,
    },
    "general": {
        "description": "General/default scenes - balanced coverage",
        "required_categories": ["主要キャラ", "核心設定", "伏線", "武術・スキル", "地理・勢力", "アイテム・装備"],
        "optional_categories": [],
        "excluded_categories": [],
        "required_entities": ["protagonist", "key_item", "key_location"],
        "min_category_preservation_rate": 0.8,
        "min_entity_retention_rate": 0.75,
    },
}

# Test cases for accuracy validation
# Each test case has: input text, scene_type, expected categories, expected key entities
ACCURACY_TEST_CASES: List[Dict[str, Any]] = [
    {
        "name": "combat_basic",
        "scene_type": "combat",
        "text": (
            "アルカディアは聖剣エクスカリバーを抜き、魔王ヴォルケインに向かって迅雷を放った。"
            "剣閃が空を裂き、敵の魔力を打ち砕く。王都グランヴァルの運命が今、決まる。"
        ),
        "expected_categories": ["武術・スキル", "主要キャラ", "アイテム・装備"],
        "expected_entities": ["アルカディア", "エクスカリバー", "ヴォルケイン", "迅雷"],
        "min_preservation": 0.8,
    },
    {
        "name": "daily_tavern",
        "scene_type": "daily",
        "text": (
            "アルカディアとカロルは王都グランヴァルの酒場『月光亭』でエールを傾けていた。"
            "冒険者ギルドの依頼板を見ながら、次の仕事について語り合う。"
            "カロルが持ってきた治癒のポーションを二人で分け合った。"
        ),
        "expected_categories": ["主要キャラ", "地理・勢力", "アイテム・装備"],
        "expected_entities": ["アルカディア", "カロル", "王都グランヴァル", "冒険者ギルド", "治癒のポーション"],
        "min_preservation": 0.8,
    },
{
        "name": "psychological_memory",
        "scene_type": "psychological",
        "text": (
            "夜、アルカディアは独り王宮のバルコニーに立っていた。"
            "かつて師匠ガレスから教わった抜刀術・迅雷の真意を、今になって問い直す。"
            "『力とは守るためにある』という言葉が、胸に重く響く。"
            "魔王ヴォルケインとの因縁、そして聖剣エクスカリバーの封印の謎。"
        ),
        "expected_categories": ["主要キャラ", "伏線", "武術・スキル"],
        "expected_entities": ["アルカディア", "ガレス", "ヴォルケイン", "エクスカリバー", "迅雷"],
        "min_preservation": 0.8,
    },
    {
        "name": "political_council",
        "scene_type": "political",
        "text": (
            "王都グランヴァルの玉座の間で、宰相バルガスと商人ギルド長ミレナが対峙する。"
            "関税引き上げを巡る交渉は決裂し、辺境警備隊の動向が鍵を握る。"
            "古代の条約『エルシオン協定』が引き合いに出され、同盟の行方が不透明になる。"
        ),
        "expected_categories": ["地理・勢力", "伏線", "主要キャラ", "核心設定"],
        "expected_entities": ["王都グランヴァル", "バルガス", "ミレナ", "商人ギルド", "辺境警備隊", "エルシオン協定", "関税"],
        "min_preservation": 0.75,
    },
]

# Scene type keyword mapping for detection testing
SCENE_TYPE_KEYWORDS = {
    "combat": ["戦闘", "決闘", "討伐", "撃破", "襲撃", "激突", "交戦", "斬", "剣", "魔王", "抜刀", "迅雷"],
    "daily": ["日常", "宴", "酒場", "休息", "街歩き", "料理", "雑談", "市場", "買い物", "会話"],
    "psychological": ["心理", "葛藤", "苦悩", "トラウマ", "独白", "疑念", "迷い", "回想", "記憶", "内面"],
    "political": ["会議", "議会", "政略", "関税", "条約", "宣戦", "同盟", "陰謀", "外交", "交渉", "宰相", "ギルド"],
}

__all__ = [
    "SCENE_ANNOTATIONS",
    "ACCURACY_TEST_CASES",
    "SCENE_TYPE_KEYWORDS",
]