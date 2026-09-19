"""Inline beat tag parser for script annotations."""
from __future__ import annotations

import re
from typing import Optional

from src.annotations.beat import EmotionalBeat
from src.pipeline.emotional_residue import EmotionType
from src.pipeline.character_dict import load_character_dict


# インラインタグ正規表現
# [beat:emotion+delta cause="reason" hidden]
BEAT_PATTERN = re.compile(
    r'\[beat:(\w+)([+-]\d+\.?\d*)\s*(?:cause="([^"]*)")?\s*(hidden)?\]',
    re.IGNORECASE
)

# 感情タイプ正規化マップ
EMOTION_ALIASES = {
    "aff": "affection",
    "ten": "tension",
    "fea": "fear",
    "tru": "trust",
    "int": "intimacy",
    "jel": "jealousy",
    "ang": "anger",
    "sad": "sadness",
    "sur": "surprise",
    "dis": "disgust",
    "gui": "sadness",  # guilt -> sadness
}


def normalize_emotion(emotion_str: str) -> EmotionType:
    """感情文字列をEmotionTypeに正規化"""
    emo_lower = emotion_str.lower()
    if emo_lower in EMOTION_ALIASES:
        emo_lower = EMOTION_ALIASES[emo_lower]
    try:
        return EmotionType(emo_lower)
    except ValueError:
        # デフォルトはaffection
        return EmotionType.AFFECTION


def parse_beats(
    text: str,
    episode: int,
    scene: int = 1,
    character_dict: Optional[set[str]] = None,
) -> tuple[str, list[EmotionalBeat]]:
    """脚本からインラインビートタグを抽出し、クリーンテキストとビートリストを返す
    
    Args:
        text: 脚本テキスト
        episode: エピソード番号
        scene: シーン番号
        character_dict: キャラクター辞書（発言者推定用）
        
    Returns:
        (クリーンテキスト, 抽出ビートリスト)
    """
    if character_dict is None:
        character_dict = load_character_dict()
    
    beats = []
    clean_lines = []
    beat_id_counter = 0
    
    for line in text.split('\n'):
        # その行のタグを全て抽出
        line_beats = []
        last_end = 0
        clean_line_parts = []
        
        for match in BEAT_PATTERN.finditer(line):
            emotion_str, delta_str, cause, hidden_flag = match.groups()
            start, end = match.span()
            
            # タグ前のテキストを保持
            clean_line_parts.append(line[last_end:start])
            last_end = end
            
            # delta パース
            try:
                delta = float(delta_str)
            except ValueError:
                continue
            
            # 感情タイプ正規化
            emotion = normalize_emotion(emotion_str)
            
            # 原因デフォルト
            if not cause:
                cause = f"ep{episode} inline annotation"
            
            # hidden フラグ
            hidden = bool(hidden_flag)
            
            # 発言者推定（直前の行から）
            speaker = _estimate_speaker(text, match.start(), character_dict)
            target = _estimate_target(text, match.start(), character_dict, speaker)
            
            if not speaker or not target:
                # 推定できない場合はスキップ
                continue
            
            beat = EmotionalBeat(
                episode=episode,
                scene=scene,
                source=speaker,
                target=target,
                emotion=emotion,
                delta=delta,
                cause=cause,
                confidence=0.9,  # インラインタグは高信頼度
                hidden=hidden,
            )
            line_beats.append(beat)
            beats.append(beat)
            beat_id_counter += 1
        
        # 残りのテキスト追加
        clean_line_parts.append(line[last_end:])
        clean_lines.append(''.join(clean_line_parts))
    
    return '\n'.join(clean_lines), beats


def _estimate_speaker(
    full_text: str,
    tag_position: int,
    character_dict: set[str],
) -> Optional[str]:
    """タグ位置より前のテキストから発言者を推定"""
    # タグ位置より前のテキストを取得
    prefix = full_text[:tag_position]
    
    # 最後のセリフ行を探す（「キャラ名「」」パターン）
    import re
    # 逆順で検索
    lines = prefix.split('\n')
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        # 「キャラ名「セリフ」」パターン
        match = re.match(r'^([^「\n]+)「', line)
        if match:
            speaker = match.group(1).strip()
            if speaker in character_dict:
                return speaker
            # 部分マッチ試行
            for char in character_dict:
                if char in speaker or speaker in char:
                    return char
    
    # キャラ名単独行を探す
    for line in reversed(lines):
        line = line.strip()
        if line in character_dict:
            return line
    
    return None


def _estimate_target(
    full_text: str,
    tag_position: int,
    character_dict: set[str],
    speaker: Optional[str],
) -> Optional[str]:
    """タグ位置の前後から対象を推定（簡易：発言者以外の主要キャラ）"""
    # 発言者以外で最初に見つかるキャラ名を対象とする
    prefix = full_text[:tag_position]
    
    # 近くに出現するキャラ名を探す
    import re
    found_chars = []
    for char in character_dict:
        if char != speaker:
            # 直前500文字以内に出現するか
            if char in prefix[-500:]:
                found_chars.append(char)
    
    if found_chars:
        return found_chars[-1]  # 直近のもの
    
    # フォールバック: 発言者以外の最初のキャラ
    for char in character_dict:
        if char != speaker:
            return char
    
    return None


__all__ = ["parse_beats", "normalize_emotion", "BEAT_PATTERN"]