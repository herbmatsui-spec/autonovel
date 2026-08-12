"""
SpiceGuard - 面白さの核（尖り）を自動保護するリライト支援
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Set

from src.presets.loader import load_preset


@dataclass
class SpiceElement:
    """尖り要素"""
    type: str           # "unique_metaphor", "character_voice", "plot_twist_marker", "emotional_raw", "rule_break_for_effect"
    text: str           # 元のテキスト
    position: int       # 文字位置
    priority: str       # "critical", "high", "medium", "low"
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SpiceGuard:
    """尖り保護システム"""

    # 普遍的保護パターン（全ジャンル共通）
    UNIVERSAL_PATTERNS = {
        "unique_metaphor": {
            "patterns": [
                r'(?:まるで|まるで|ようだ|かのように|ような)(.{10,60}?)(?:だ|です|。|！)',
                r'(?:かのよう|ごとく|如く)(.{5,40}?)(?:だ|です|。)',
            ],
            "priority": "high"
        },
        "plot_twist_marker": {
            "keywords": ["実は", "真実", "正体", "裏切り", "秘密", "覚醒", "真の", "隠された", "偽り", "罠"],
            "priority": "critical"
        },
        "emotional_raw": {
            "patterns": [
                r'(?:胸が|心が|背筋が|息が|震えが|涙が|熱が|冷や汗が)(?:締め付けられ|凍る|跳ねる|詰まる|止まらない|溢れる|引く|熱くなる|冷たくなる)(.{0,20}?)',
                r'(?:恐怖|怒り|喜び|悲しみ|絶望|希望|安堵|戦慄|戦慄|悔しさ|無力感|充実感)が(?:体を|心を|胸を|全身を)(.{0,20}?)',
            ],
            "priority": "high"
        },
    }

    # ジャンル別保護パターン
    GENRE_PATTERNS = {
        "zarma": {
            "catharsis_payoff": {
                "keywords": ["ざまぁ", "見返し", "無双", "圧倒的", "完全制圧", "土下座", "謝罪", "恐怖", "絶望", "無様"],
                "priority": "critical"
            },
            "villain_despair": {
                "patterns": [r'(?:敵|悪党|裏切り者|元仲間)(?:の|が)(?:顔面蒼白|青ざめ|震え|叫び|懇願|涙目)'],
                "priority": "high"
            },
            "power_gap": {
                "patterns": [r'(?:レベル|ステータス|戦力|実力)(?:差|圧倒|無効|通用しない|ゴミ|雑魚)'],
                "priority": "high"
            },
        },
        "aku_reijo": {
            "flag_avoidance": {
                "keywords": ["フラグ", "回避", "折る", "へし折", "破綻", "ルート変更", "攻略外", "隠し"],
                "priority": "critical"
            },
            "yuri_tension": {
                "keywords": ["尊い", "尊み", "推し", "百合", "ガルラブ", "キス", "抱擁", "契約", "眷属", "一生"],
                "priority": "high"
            },
        },
        "cheat_tensei": {
            "system_flavor": {
                "keywords": ["スキル習得", "レベルアップ", "ステータス", "∞", "無限", "チート", "バグ", "仕様", "デバッグ", "パッチ"],
                "priority": "high"
            },
            "efficiency_brag": {
                "keywords": ["効率", "最適解", "コスパ", "タイム", "秒殺", "ワープ", "スキップ", "自動"],
                "priority": "high"
            },
        },
        "slow_life": {
            "sensory_richness": {
                "keywords": ["香り", "香ばし", "ふわふわ", "とろけ", "さっくり", "じゅわ", "ほっこり", "ぬくもり", "優し", "美味"],
                "priority": "critical"
            },
            "daily_ritual": {
                "keywords": ["朝食", "夕食", "お茶", "パン", "野菜", "収穫", "手入れ", "掃除", "洗濯", "日課"],
                "priority": "high"
            },
        },
        "dungeon_admin": {
            "trap_creativity": {
                "keywords": ["罠", "ギミック", "仕掛け", "落とし穴", "転移", "幻覚", "毒", "麻痺", "即死", "ユニーク"],
                "priority": "high"
            },
            "monster_personality": {
                "keywords": ["忠誠", "進化", "命名", "個性", "口癖", "好物", "嫉妬", "甘え", "守護", "主"],
                "priority": "high"
            },
        },
        "modern_cheat": {
            "tech_metaphor": {
                "keywords": ["ルート権限", "管理者", "パッチ", "バグ", "チートコード", "メモリ", "プロセス", "カーネル", "API", "SQL"],
                "priority": "critical"
            },
            "reality_impact": {
                "keywords": ["現金化", "換金", "実体化", "具現化", "オーバーレイ", "AR", "同期", "リンク", "干渉"],
                "priority": "high"
            },
        },
        "ts_tensei": {
            "gender_euphoria": {
                "keywords": ["可愛い", "美少女", "女性", "少女", "乙女", "ドレス", "リボン", "髪", "声", "胸", "肌"],
                "priority": "critical"
            },
            "yuri_intimacy": {
                "keywords": ["キス", "抱擁", "膝枕", "髪梳き", "耳掃除", "添い寝", "告白", "契約", "眷属", "一生"],
                "priority": "high"
            },
        },
        "vrmmo": {
            "sync_terminology": {
                "keywords": ["フルダイブ", "同期", "神経リンク", "ハプティック", "オーバーレイ", "アバター", "NPC", "レイド", "ドロップ"],
                "priority": "high"
            },
            "reality_bleed": {
                "keywords": ["実体化", "具現化", "現実", "侵食", "統合", "境界", "溶解", "シンクロ", "量子"],
                "priority": "critical"
            },
        },
        "loop": {
            "loop_count": {
                "keywords": ["周目", "ループ", "回帰", "やり直し", "リトライ", "試行", "データ", "パターン", "収束", "最適解"],
                "priority": "critical"
            },
            "convergence": {
                "keywords": ["真エンド", "完全攻略", "全フラグ", "全回収", "確率1", "必然", "決定", "選ばれた世界線"],
                "priority": "critical"
            },
        },
    }

    def __init__(self, genre: str):
        self.genre = genre
        self.preset = load_preset(genre)
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """正規表現を事前コンパイル"""
        compiled = {}

        # 普遍パターン
        for pattern_type, config in self.UNIVERSAL_PATTERNS.items():
            if "patterns" in config:
                compiled[pattern_type] = [re.compile(p) for p in config["patterns"]]

        # ジャンル別パターン
        genre_patterns = self.GENRE_PATTERNS.get(self.genre, {})
        for pattern_type, config in genre_patterns.items():
            if "patterns" in config:
                key = f"{self.genre}_{pattern_type}"
                compiled[key] = [re.compile(p) for p in config["patterns"]]

        return compiled

    def extract_spice(self, text: str) -> List[SpiceElement]:
        """テキストから尖り要素を抽出"""
        elements = []

        # 1. 普遍パターンによる抽出
        for pattern_type, config in self.UNIVERSAL_PATTERNS.items():
            priority = config["priority"]

            if "patterns" in config:
                for pattern in self._compiled_patterns.get(pattern_type, []):
                    for match in pattern.finditer(text):
                        elements.append(SpiceElement(
                            type=pattern_type,
                            text=match.group(0),
                            position=match.start(),
                            priority=priority,
                            metadata={"matched_group": match.group(0)}
                        ))

            if "keywords" in config:
                for keyword in config["keywords"]:
                    for match in re.finditer(re.escape(keyword), text):
                        elements.append(SpiceElement(
                            type=pattern_type,
                            text=keyword,
                            position=match.start(),
                            priority=priority,
                            metadata={"keyword": keyword}
                        ))

        # 2. ジャンル別パターンによる抽出
        genre_patterns = self.GENRE_PATTERNS.get(self.genre, {})
        for pattern_type, config in genre_patterns.items():
            priority = config["priority"]
            full_type = f"{self.genre}_{pattern_type}"

            if "keywords" in config:
                for keyword in config["keywords"]:
                    for match in re.finditer(re.escape(keyword), text):
                        elements.append(SpiceElement(
                            type=full_type,
                            text=keyword,
                            position=match.start(),
                            priority=priority,
                            metadata={"keyword": keyword}
                        ))

            if "patterns" in config:
                for pattern in self._compiled_patterns.get(full_type, []):
                    for match in pattern.finditer(text):
                        elements.append(SpiceElement(
                            type=full_type,
                            text=match.group(0),
                            position=match.start(),
                            priority=priority,
                            metadata={"matched_group": match.group(0)}
                        ))

        # 3. キャラクター固有要素（プリセットから抽出）
        elements.extend(self._extract_character_elements(text))

        # 4. 重複除去・ソート
        return self._deduplicate_and_sort(elements)

    def _extract_character_elements(self, text: str) -> List[SpiceElement]:
        """プリセットのキャラクター定義から固有要素を抽出"""
        elements = []
        chars = self.preset.get("characters", {})
        archetypes = chars.get("archetypes", {})

        for proto_name, proto in archetypes.items():
            speech = proto.get("speech_patterns", {})

            # 禁句・キャッチフレーズ
            for word in speech.get("forbidden_words", []) + speech.get("catchphrases", []):
                for match in re.finditer(re.escape(word), text):
                    elements.append(SpiceElement(
                        type="character_voice",
                        text=word,
                        position=match.start(),
                        priority="high",
                        metadata={"character": proto_name, "word_type": "forbidden" if word in speech.get("forbidden_words", []) else "catchphrase"}
                    ))

        return elements

    def _deduplicate_and_sort(self, elements: List[SpiceElement]) -> List[SpiceElement]:
        """重複除去・優先度順ソート"""
        # 位置・タイプ・テキストで重複判定
        seen: Set[tuple] = set()
        unique = []

        for elem in elements:
            key = (elem.type, elem.text, elem.position)
            if key not in seen:
                seen.add(key)
                unique.append(elem)

        # 優先度順ソート
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unique.sort(key=lambda x: (priority_order.get(x.priority, 4), x.position))

        return unique

    def inject_markers(self, text: str, elements: List[SpiceElement]) -> str:
        """尖り要素を保護マーカーで囲む"""
        # 後ろから置換（位置がずれないように）
        sorted_elements = sorted(elements, key=lambda x: x.position, reverse=True)

        result = text
        for elem in sorted_elements:
            pos = elem.position
            length = len(elem.text)
            if pos >= 0 and length > 0 and pos + length <= len(result):
                # 元のテキストと一致するか確認
                if result[pos:pos+length] == elem.text:
                    marker_id = f"{elem.type}_{pos}"
                    before = result[:pos]
                    target = result[pos:pos+length]
                    after = result[pos+length:]
                    result = before + f"<<<SPICE:{marker_id}>>> {target} <<</SPICE>>>" + after

        return result

    def remove_markers(self, text: str) -> str:
        """SPICEマーカーを除去"""
        return re.sub(r'<<<SPICE:[^>]+>>>|<<</SPICE>>>', '', text)

    def build_rewrite_prompt(self, content: str, improvements: List[str], elements: List[SpiceElement]) -> str:
        """SpiceGuard付きリライトプロンプト構築"""
        protected_content = self.inject_markers(content, elements)

        improvements_text = "\n".join(f"- {imp}" for imp in improvements)

        prompt = f"""以下の小説を改善せよ。ただし、<<<SPICE:...>>> で囲まれた部分は
『絶対に変更するな。一文字も触るな。そこがこの話の『命』だ。』

【改善指示】
{improvements_text}

【原文】
{protected_content}

改善後の本文のみを出力せよ。SPICEマーカーはそのまま残せ。"""

        return prompt

    def clean_output(self, text: str) -> str:
        """出力からSPICEマーカーを除去"""
        return self.remove_markers(text)


# 便利関数
def create_spice_guard(genre: str) -> SpiceGuard:
    """SpiceGuardインスタンス生成"""
    return SpiceGuard(genre)
