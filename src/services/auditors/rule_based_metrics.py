from __future__ import annotations
import re
import math
from typing import NamedTuple

class RhythmScore(NamedTuple):
    sentence_count: int
    avg_length: float
    std_dev: float
    score: float  # 0.0 - 100.0

def calculate_sentence_rhythm(text: str) -> RhythmScore:
    """文長の平均と分散からリズム（緩急）スコアを計算する。"""
    sentences = [s.strip() for s in re.split(r'[。！？\n]', text) if s.strip()]
    if not sentences:
        return RhythmScore(0, 0.0, 0.0, 50.0)
    lengths = [len(s) for s in sentences]
    avg = sum(lengths) / len(lengths)
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    # Web小説の理想: 平均25〜40文字、標準偏差15〜30（短文と長文のメリハリ）
    ideal_std = 20.0
    score = max(0.0, min(100.0, 100.0 - abs(std_dev - ideal_std) * 2.5))
    return RhythmScore(len(sentences), avg, std_dev, score)

class DialogueScore(NamedTuple):
    dialogue_char_count: int
    total_char_count: int
    ratio: float  # 0.0 - 1.0
    score: float  # 0.0 - 100.0

def calculate_dialogue_ratio(text: str) -> DialogueScore:
    """カギ括弧「」内の台詞比率とスコアを計算する。"""
    total_chars = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    if total_chars == 0:
        return DialogueScore(0, 0, 0.0, 50.0)
    dialogues = re.findall(r'「(.*?)」', text, re.DOTALL)
    dialogue_chars = sum(len(d) for d in dialogues)
    ratio = dialogue_chars / total_chars
    # 黄金比: 30%〜45% を 100点、乖離に応じて減点
    if 0.30 <= ratio <= 0.45:
        score = 100.0
    elif ratio < 0.30:
        score = max(20.0, 100.0 - (0.30 - ratio) * 250.0)
    else:
        score = max(20.0, 100.0 - (ratio - 0.45) * 200.0)
    return DialogueScore(dialogue_chars, total_chars, ratio, score)

def calculate_kanji_ratio(text: str) -> float:
    """漢字の含有率（0.0 - 1.0）を計算する。"""
    total = len(re.sub(r'\s', '', text))
    if total == 0:
        return 0.0
    kanji_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    return kanji_count / total

AI_CLICHE_PATTERNS = [
    r"〜だったのだ",
    r"言葉を失った",
    r"胸の奥底で",
    r"運命の歯車が",
    r"一筋の光が",
    r"予感を禁じ得なかった",
    r"何かが始まろうとしていた",
]

def detect_ai_cliches(text: str) -> list[str]:
    """本文中のAI頻出定型句を検出する。"""
    found = []
    for pat in AI_CLICHE_PATTERNS:
        if re.search(pat, text):
            found.append(pat)
    return found

def evaluate_cliffhanger_ending(text: str) -> float:
    """エピソード末尾の引き強度（0.0 - 100.0）を評価する。"""
    tail = text.strip()[-200:]
    score = 50.0
    if re.search(r'[！？!?]$', tail):
        score += 20.0
    if tail.endswith("」"):
        score += 15.0
    if re.search(r'(まさか|突如|その時|現れた|気付いた|信じられない)', tail):
        score += 15.0
    return min(100.0, score)

def verify_character_suffixes(dialogues: list[str], patterns: list[str]) -> float:
    """キャラクターの台詞が設定された語尾パターンに合致しているかを静的検証（0.0 - 100.0）"""
    if not dialogues or not patterns:
        return 100.0
    combined_pattern = "|".join(patterns)
    matched = sum(1 for d in dialogues if re.search(combined_pattern, d))
    return (matched / len(dialogues)) * 100.0

