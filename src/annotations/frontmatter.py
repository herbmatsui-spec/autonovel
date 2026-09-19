"""YAML frontmatter parser for emotional beat annotations."""
from __future__ import annotations

import yaml
from typing import Optional

from src.annotations.beat import EmotionalBeat, ParsedScript
from src.pipeline.emotional_residue import EmotionType


# フロントマター区切りマーカー
FRONTMATTER_DELIMITER = "---"


def parse_frontmatter(text: str) -> tuple[str, list[EmotionalBeat]]:
    """YAMLフロントマターからビートを抽出
    
    形式:
    ---
    beats:
      - source: "A"
        target: "B"
        emotion: "fear"
        delta: 0.6
        cause: "ep14 betrayal"
        confidence: 0.9
        hidden: true
    ---
    
    Args:
        text: 脚本テキスト（フロントマター含む）
        
    Returns:
        (フロントマター除去後のテキスト, 抽出ビートリスト)
    """
    beats = []
    clean_text = text
    
    # フロントマター検出
    if not text.startswith(FRONTMATTER_DELIMITER):
        return text, []
    
    # 2つ目のデリミタを探す
    lines = text.split('\n')
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == FRONTMATTER_DELIMITER:
            end_idx = i
            break
    
    if end_idx == -1:
        # 閉じタグなし
        return text, []
    
    # フロントマター部分をパース
    frontmatter_yaml = '\n'.join(lines[1:end_idx])
    try:
        fm_data = yaml.safe_load(frontmatter_yaml)
    except yaml.YAMLError:
        return text, []
    
    if not fm_data or "beats" not in fm_data:
        return text, []
    
    # 残りのテキスト（フロントマター以降）
    clean_text = '\n'.join(lines[end_idx + 1:]).lstrip('\n')
    
    # ビートリスト構築
    for idx, beat_data in enumerate(fm_data["beats"]):
        try:
            beat = EmotionalBeat(
                episode=beat_data.get("episode", 1),
                scene=beat_data.get("scene", 1),
                source=beat_data["source"],
                target=beat_data["target"],
                emotion=EmotionType(beat_data["emotion"]),
                delta=float(beat_data["delta"]),
                cause=beat_data.get("cause", "frontmatter annotation"),
                beat_id=beat_data.get("beat_id", ""),
                confidence=float(beat_data.get("confidence", 1.0)),
                hidden=bool(beat_data.get("hidden", False)),
                metadata=beat_data.get("metadata", {}),
            )
            beats.append(beat)
        except (KeyError, ValueError, TypeError) as e:
            # 不正なビートはスキップ
            continue
    
    return clean_text, beats


def serialize_frontmatter(beats: list[EmotionalBeat]) -> str:
    """ビートリストをYAMLフロントマター文字列に変換"""
    fm_data = {"beats": [beat.to_dict() for beat in beats]}
    yaml_str = yaml.dump(fm_data, allow_unicode=True, sort_keys=False)
    return f"{FRONTMATTER_DELIMITER}\n{yaml_str}{FRONTMATTER_DELIMITER}\n"


__all__ = ["parse_frontmatter", "serialize_frontmatter", "FRONTMATTER_DELIMITER"]