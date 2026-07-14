"""
config/sharp_edge_vocabulary.py
「削ってはいけない角」を定義する語彙集モジュール。

高品質化の過程で角が削られるのを防ぐため、
3つの角を固定し、品質監査で保全を強制する。
"""
from typing import Dict, List

SHARP_EDGE_TYPES: List[str] = [
    "ending_pullback",
    "protagonist_flaw",
    "abnormal_dialogue",
    "sharp_conflict",
]

SHARP_EDGE_DESCRIPTIONS: Dict[str, str] = {
    "ending_pullback": "結末の引き方（期待を裏切る余韻のある終わり方）",
    "protagonist_flaw": "主人公の1つの欠陥（共感を誘う弱点）",
    "abnormal_dialogue": "異常なセリフ（キャラクターを際立たせる非日常的な発言）",
}

SHARP_EDGE_KEY_PHRASE_GUIDANCE: Dict[str, str] = {
    "ending_pullback": "本文中の結末に関する具体的描写（20文字以内）",
    "protagonist_flaw": "本文中の主人公欠陥を示す直接的表現（20文字以内）",
    "abnormal_dialogue": "本文から直接引用した異常セリフ（20文字以内）",
}
