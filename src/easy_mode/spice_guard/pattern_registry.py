"""
SpiceGuard パターンレジストリ
パターン定義・正規表現コンパイル・キャッシュを管理
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Pattern

# ==========================================
# 普遍的保護パターン（全ジャンル共通）
# ==========================================
UNIVERSAL_PATTERNS: Dict[str, Dict[str, Any]] = {
    "unique_metaphor": {
        "patterns": [
            r"(?:まるで|まるで|ようだ|かのように|ような)(.{10,60}?)(?:だ|です|。|！)",
            r"(?:かのよう|ごとく|如く)(.{5,40}?)(?:だ|です|。)",
        ],
        "priority": "high",
    },
    "plot_twist_marker": {
        "keywords": [
            "実は",
            "真実",
            "正体",
            "裏切り",
            "秘密",
            "覚醒",
            "真の",
            "隠された",
            "偽り",
            "罠",
        ],
        "priority": "critical",
    },
    "emotional_raw": {
        "patterns": [
            r"(?:胸が|心が|背筋が|息が|震えが|涙が|熱が|冷や汗が)(?:締め付けられ|凍る|跳ねる|詰まる|止まらない|溢れる|引く|熱くなる|冷たくなる)(.{0,20}?)",
            r"(?:恐怖|怒り|喜び|悲しみ|絶望|希望|安堵|戦慄|戦慄|悔しさ|無力感|充実感)が(?:体を|心を|胸を|全身を)(.{0,20}?)",
        ],
        "priority": "high",
    },
}


# ==========================================
# ジャンル別保護パターン
# ==========================================
GENRE_PATTERNS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "zarma": {
        "catharsis_payoff": {
            "keywords": [
                "ざまぁ",
                "見返し",
                "無双",
                "圧倒的",
                "完全制圧",
                "土下座",
                "謝罪",
                "恐怖",
                "絶望",
                "無様",
            ],
            "priority": "critical",
        },
        "villain_despair": {
            "patterns": [
                r"(?:敵|悪党|裏切り者|元仲間)(?:の|が)(?:顔面蒼白|青ざめ|震え|叫び|懇願|涙目)"
            ],
            "priority": "high",
        },
        "power_gap": {
            "patterns": [
                r"(?:レベル|ステータス|戦力|実力)(?:差|圧倒|無効|通用しない|ゴミ|雑魚)"
            ],
            "priority": "high",
        },
    },
    "aku_reijo": {
        "flag_avoidance": {
            "keywords": [
                "フラグ",
                "回避",
                "折る",
                "へし折",
                "破綻",
                "ルート変更",
                "攻略外",
                "隠し",
            ],
            "priority": "critical",
        },
        "yuri_tension": {
            "keywords": [
                "尊い",
                "尊み",
                "推し",
                "百合",
                "ガルラブ",
                "キス",
                "抱擁",
                "契約",
                "眷属",
                "一生",
            ],
            "priority": "high",
        },
    },
    "cheat_tensei": {
        "system_flavor": {
            "keywords": [
                "スキル習得",
                "レベルアップ",
                "ステータス",
                "∞",
                "無限",
                "チート",
                "バグ",
                "仕様",
                "デバッグ",
                "パッチ",
            ],
            "priority": "high",
        },
        "efficiency_brag": {
            "keywords": [
                "効率",
                "最適解",
                "コスパ",
                "タイム",
                "秒殺",
                "ワープ",
                "スキップ",
                "自動",
            ],
            "priority": "high",
        },
    },
    "slow_life": {
        "sensory_richness": {
            "keywords": [
                "香り",
                "香ばし",
                "ふわふわ",
                "とろけ",
                "さっくり",
                "じゅわ",
                "ほっこり",
                "ぬくもり",
                "優し",
                "美味",
            ],
            "priority": "critical",
        },
        "daily_ritual": {
            "keywords": [
                "朝食",
                "夕食",
                "お茶",
                "パン",
                "野菜",
                "収穫",
                "手入れ",
                "掃除",
                "洗濯",
                "日課",
            ],
            "priority": "high",
        },
    },
    "dungeon_admin": {
        "trap_creativity": {
            "keywords": [
                "罠",
                "ギミック",
                "仕掛け",
                "落とし穴",
                "転移",
                "幻覚",
                "毒",
                "麻痺",
                "即死",
                "ユニーク",
            ],
            "priority": "high",
        },
        "monster_personality": {
            "keywords": [
                "忠誠",
                "進化",
                "命名",
                "個性",
                "口癖",
                "好物",
                "嫉妬",
                "甘え",
                "守護",
                "主",
            ],
            "priority": "high",
        },
    },
    "modern_cheat": {
        "tech_metaphor": {
            "keywords": [
                "ルート権限",
                "管理者",
                "パッチ",
                "バグ",
                "チートコード",
                "メモリ",
                "プロセス",
                "カーネル",
                "API",
                "SQL",
            ],
            "priority": "critical",
        },
        "reality_impact": {
            "keywords": [
                "現金化",
                "換金",
                "実体化",
                "具現化",
                "オーバーレイ",
                "AR",
                "同期",
                "リンク",
                "干渉",
            ],
            "priority": "high",
        },
    },
    "ts_tensei": {
        "gender_euphoria": {
            "keywords": [
                "可愛い",
                "美少女",
                "女性",
                "少女",
                "乙女",
                "ドレス",
                "リボン",
                "髪",
                "声",
                "胸",
                "肌",
            ],
            "priority": "critical",
        },
        "yuri_intimacy": {
            "keywords": [
                "キス",
                "抱擁",
                "膝枕",
                "髪梳き",
                "耳掃除",
                "添い寝",
                "告白",
                "契約",
                "眷属",
                "一生",
            ],
            "priority": "high",
        },
    },
    "vrmmo": {
        "sync_terminology": {
            "keywords": [
                "フルダイブ",
                "同期",
                "神経リンク",
                "ハプティック",
                "オーバーレイ",
                "アバター",
                "NPC",
                "レイド",
                "ドロップ",
            ],
            "priority": "high",
        },
        "reality_bleed": {
            "keywords": [
                "実体化",
                "具現化",
                "現実",
                "侵食",
                "統合",
                "境界",
                "溶解",
                "シンクロ",
                "量子",
            ],
            "priority": "critical",
        },
    },
    "loop": {
        "loop_count": {
            "keywords": [
                "周目",
                "ループ",
                "回帰",
                "やり直し",
                "リトライ",
                "試行",
                "データ",
                "パターン",
                "収束",
                "最適解",
            ],
            "priority": "critical",
        },
        "convergence": {
            "keywords": [
                "真エンド",
                "完全攻略",
                "全フラグ",
                "全回収",
                "確率1",
                "必然",
                "決定",
                "選ばれた世界線",
            ],
            "priority": "critical",
        },
    },
}


# ==========================================
# コンパイル済みパターンキャッシュ
# ==========================================
class CompiledPatternCache:
    """正規表現コンパイル結果のキャッシュ"""

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, List[Pattern[str]]]] = {}

    def get(self, genre: str) -> Dict[str, List[Pattern[str]]]:
        if genre not in self._cache:
            self._cache[genre] = self._compile_for_genre(genre)
        return self._cache[genre]

    def _compile_for_genre(self, genre: str) -> Dict[str, List[Pattern[str]]]:
        compiled: Dict[str, List[Pattern[str]]] = {}

        # 普遍パターン
        for pattern_type, config in UNIVERSAL_PATTERNS.items():
            if "patterns" in config:
                compiled[pattern_type] = [re.compile(p) for p in config["patterns"]]

        # ジャンル別パターン
        genre_patterns = GENRE_PATTERNS.get(genre, {})
        for pattern_type, config in genre_patterns.items():
            if "patterns" in config:
                key = f"{genre}_{pattern_type}"
                compiled[key] = [re.compile(p) for p in config["patterns"]]

        return compiled

    def clear(self) -> None:
        """キャッシュクリア（テスト用）"""
        self._cache.clear()


# グローバルキャッシュインスタンス
pattern_cache = CompiledPatternCache()


def get_compiled_patterns(genre: str) -> Dict[str, List[re.Pattern]]:
    """ジャンルのコンパイル済みパターンを取得"""
    return pattern_cache.get(genre)


def get_universal_patterns() -> Dict[str, Dict[str, Any]]:
    """普遍パターン定義を取得"""
    return UNIVERSAL_PATTERNS


def get_genre_patterns(genre: str) -> Dict[str, Dict[str, Any]]:
    """ジャンル別パターン定義を取得"""
    return GENRE_PATTERNS.get(genre, {})
