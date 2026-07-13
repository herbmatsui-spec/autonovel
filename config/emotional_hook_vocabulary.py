"""
config/emotional_hook_vocabulary.py
心理的「刺さり」を表現する感情起点の語彙集モジュール。

高品質≠面白い問題を解決するため、まず「何を感じさせるか」を
1行で定義し、品質はその感情の従属変数として扱う。
"""
from typing import Dict, Tuple

EMOTIONAL_HOOKS: Dict[str, Tuple[str, str, int]] = {
    "catharsis": (
        "カタルシス",
        "長い苦悩の末に訪れる解放と浄化",
        85,
    ),
    "empathy_peak": (
        "共感の最深",
        "他者の痛みを自分のこととして感じる瞬間",
        70,
    ),
    "chilling": (
        "背筋の寒さ",
        "理解不能な脅威に触れる戦慄",
        90,
    ),
    "righteous_anger": (
        "義憤",
        "不正への怒りが正義の行動に変わる熱量",
        80,
    ),
    "triumph": (
        " Triumph ",
        "絶対的逆境を突破した瞬間の高揚",
        95,
    ),
    "serenity": (
        "静寂の喜び",
        "日常の中に息づく小さな至福",
        40,
    ),
    "nostalgia": (
        "郷愁",
        "失われた時間へのノスタルジックな郷愁",
        55,
    ),
    "awe": (
        "畏敬",
        "偉大な存在や事象に対する震撼と尊敬",
        75,
    ),
}


def get_hook_peak_tension(hook_name: str) -> int:
    """感情起点名から推奨tensionピーク値を取得する。未知フックは50を返す。"""
    entry = EMOTIONAL_HOOKS.get(hook_name)
    if entry is None:
        return 50
    return entry[2]


def validate_hook(hook_name: str) -> bool:
    """感情起点名が EMOTIONAL_HOOKS に存在するかを返す。"""
    return hook_name in EMOTIONAL_HOOKS
