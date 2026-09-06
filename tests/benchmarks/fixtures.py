"""Long novel test fixture generator."""
from __future__ import annotations

import random
from typing import List, Dict, Any
from dataclasses import dataclass, field


# 日本語の固有名詞プール
CHARACTER_NAMES = [
    "アルカディア", "ヴォルケイン", "カロル", "バルガス", "エレナ", "ガレス", "ミレナ", "ドリアン",
    "シルヴィア", "カシウス", "リディア", "トーリン", "フェリシア", "マルクス", "アリア", "ゼノン"
]

LOCATION_NAMES = [
    "王都グランヴァル", "辺境の村ルミナ", "魔王城ドルグ", "聖域エルシオン", "商業都市ミラベル",
    "古代遺跡ゾルタン", "竜の巣窟", "精霊の森", "氷の要塞", "砂漠のオアシス"
]

ITEM_NAMES = [
    "聖剣エクスカリバー", "魔導書グリモア", "竜の牙", "精霊の指輪", "治癒のポーション",
    "古代の地図", "王家の印章", "闇の結晶", "光の欠片", "時の砂時計"
]

SKILL_NAMES = [
    "抜刀術・迅雷", "火球術", "治癒の光", "瞬間移動", "念動力",
    "剣気・真空斬", "魔力吸収", "予知夢", "分身術", "結界展開"
]

FACTION_NAMES = [
    "王国軍", "魔王軍", "商人ギルド", "冒険者ギルド", "神殿騎士団",
    "暗殺者集団", "錬金術師協会", "吟遊詩人の会", "辺境警備隊", "王立図書館"
]

SCENE_TEMPLATES = {
    "combat": [
        "{char1}は{char2}と{location}で激突した。{skill}を繰り出し、{item}が光る。",
        "{char1}は{enemy}の襲撃を{skill}で迎撃した。{location}の地面が砕け散る。",
        "決戦の時、{char1}は{char2}と{location}で向き合う。{item}を構え、{skill}を放つ。",
    ],
    "daily": [
        "{char1}は{location}の酒場で{char2}と酒を酌み交わす。{item}の話で盛り上がる。",
        "休息の日、{char1}は{location}の市場を散策する。{char2}と偶然出会い、{item}を買う。",
        "{char1}と{char2}は{location}で宴会を開く。{item}を囲み、{skill}の噂話に花が咲く。",
    ],
    "psychological": [
        "{char1}は{location}で独り、{char2}への想いを胸に{skill}の修行に励む。",
        "夜、{char1}は{location}で{char2}との過去を回想する。{item}を握りしめ、葛藤する。",
        "{char1}は{location}で{char2}の裏切りを知り、{skill}の意味を問い直す。",
    ],
    "political": [
        "{char1}は{location}の会議で{char2}と{skill}を巡り議論する。{faction}の思惑が交錯する。",
        "王都{location}で{char1}と{char2}が{item}の所有権を争う。{faction}が介入する。",
        "{char1}は{location}で{char2}と同盟を結ぶ。{faction}の均衡が崩れる。",
    ],
}


@dataclass
class EpisodeData:
    """Single episode data."""
    ep_num: int
    scene_type: str
    characters: List[str]
    location: str
    items: List[str]
    skills: List[str]
    factions: List[str]
    text: str
    summary: str
    key_entities: List[str] = field(default_factory=list)


@dataclass
class LongNovelData:
    """Generated long novel data."""
    title: str
    total_episodes: int
    episodes: List[EpisodeData]
    global_entities: Dict[str, List[str]] = field(default_factory=dict)


class LongNovelGenerator:
    """Generates synthetic long-form novels for benchmarking."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.used_names = set()
        self.used_locations = set()
        self.used_items = set()
        self.used_skills = set()
        self.used_factions = set()

    def _pick_unique(self, pool: List[str], used: set, count: int = 1) -> List[str]:
        """Pick unique items from pool."""
        available = [x for x in pool if x not in used]
        if len(available) < count:
            # Reset if exhausted
            used.clear()
            available = pool
        picked = random.sample(available, min(count, len(available)))
        used.update(picked)
        return picked

    def generate_episode(self, ep_num: int, scene_type: str = None) -> EpisodeData:
        """Generate a single episode."""
        if scene_type is None:
            scene_type = random.choice(list(SCENE_TEMPLATES.keys()))

        # Pick entities for this episode
        chars = self._pick_unique(CHARACTER_NAMES, self.used_names, 3)
        location = self._pick_unique(LOCATION_NAMES, self.used_locations, 1)[0]
        items = self._pick_unique(ITEM_NAMES, self.used_items, 2)
        skills = self._pick_unique(SKILL_NAMES, self.used_skills, 2)
        factions = self._pick_unique(FACTION_NAMES, self.used_factions, 1)

        # Generate text from template
        template = random.choice(SCENE_TEMPLATES[scene_type])
        text = template.format(
            char1=chars[0],
            char2=chars[1],
            enemy=chars[2],
            location=location,
            item=items[0],
            skill=skills[0],
            faction=factions[0],
        )

        # Add more detail to make it longer
        detail_templates = {
            "combat": f" {chars[0]}の{skills[1]}が{chars[2]}を直撃し、{location}に衝撃波が走る。{items[1]}が反応し、戦況が一変する。",
            "daily": f" {chars[0]}と{chars[1]}は{items[1]}を分け合いながら、{factions[0]}の動向について語り合う。夜が更ける。",
            "psychological": f" {chars[0]}の心に{chars[2]}の影がよぎる。{skills[1]}の真意を探るべく、{location}の奥へ進む。",
            "political": f" {factions[0]}の代表{chars[2]}が提案を持ちかける。{items[1]}を賭けた駆け引きが始まる。",
        }
        text += detail_templates.get(scene_type, "")

        # Summary
        summary = f"第{ep_num}話: {chars[0]}と{chars[1]}が{location}で{scene_type}シーンを展開。{items[0]}と{skills[0]}が鍵となる。"

        # Key entities for accuracy testing
        key_entities = chars + [location] + items + skills + factions

        return EpisodeData(
            ep_num=ep_num,
            scene_type=scene_type,
            characters=chars,
            location=location,
            items=items,
            skills=skills,
            factions=factions,
            text=text,
            summary=summary,
            key_entities=key_entities,
        )

    def generate_novel(self, total_episodes: int = 100, scene_distribution: Dict[str, float] = None) -> LongNovelData:
        """Generate a full novel with specified episode count."""
        if scene_distribution is None:
            scene_distribution = {"combat": 0.3, "daily": 0.3, "psychological": 0.2, "political": 0.2}

        # Normalize distribution
        total_weight = sum(scene_distribution.values())
        scene_distribution = {k: v / total_weight for k, v in scene_distribution.items()}

        # Determine scene type for each episode
        scene_types = []
        for scene_type, weight in scene_distribution.items():
            count = int(total_episodes * weight)
            scene_types.extend([scene_type] * count)
        # Fill remaining
        while len(scene_types) < total_episodes:
            scene_types.append(random.choice(list(scene_distribution.keys())))
        random.shuffle(scene_types)

        episodes = []
        for i, scene_type in enumerate(scene_types, 1):
            ep = self.generate_episode(i, scene_type)
            episodes.append(ep)

        # Build global entity index
        global_entities = {
            "characters": list(self.used_names),
            "locations": list(self.used_locations),
            "items": list(self.used_items),
            "skills": list(self.used_skills),
            "factions": list(self.used_factions),
        }

        return LongNovelData(
            title=f"生成長編小説_{total_episodes}話",
            total_episodes=total_episodes,
            episodes=episodes,
            global_entities=global_entities,
        )


def generate_long_novel(ep_count: int, seed: int = 42) -> LongNovelData:
    """Convenience function to generate a long novel."""
    generator = LongNovelGenerator(seed)
    return generator.generate_novel(ep_count)


__all__ = [
    "LongNovelGenerator",
    "LongNovelData",
    "EpisodeData",
    "generate_long_novel",
]