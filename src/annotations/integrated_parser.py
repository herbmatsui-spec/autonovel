"""Integrated beat parser combining frontmatter and inline tags."""
from __future__ import annotations

import logging
from typing import Optional

from src.annotations.beat import EmotionalBeat, ParsedScript
from src.annotations.frontmatter import parse_frontmatter
from src.annotations.parser import parse_beats

logger = logging.getLogger(__name__)


class BeatParser:
    """インラインタグとフロントマターを統合パース"""
    
    def __init__(self, character_dict: Optional[set[str]] = None):
        self.character_dict = character_dict

    def parse_script(self, script: str, episode: int, scene: int = 1) -> ParsedScript:
        """脚本から全ビートを抽出（フロントマター優先）"""
        # 1. フロントマターを先にパース
        clean_text, frontmatter_beats = parse_frontmatter(script)
        
        # 2. 残りテキストからインラインタグをパース
        inline_clean, inline_beats = parse_beats(
            clean_text, episode, scene, self.character_dict
        )
        
        # 3. 統合（フロントマター優先でマージ）
        all_beats = self._merge_beats(frontmatter_beats, inline_beats)
        
        return ParsedScript(
            clean_text=inline_clean,
            beats=all_beats,
            frontmatter_beats=frontmatter_beats,
            inline_beats=inline_beats,
        )

    def _merge_beats(
        self,
        frontmatter_beats: list,
        inline_beats: list,
    ) -> list[EmotionalBeat]:
        """ビートリストをマージ（フロントマター優先）
        
        同一 (episode, scene, source, target, emotion) の場合、
        フロントマターの値を採用し、インラインはスキップ（警告ログ）
        """
        merged = {}
        conflicts = []
        
        # フロントマターを先に登録（高優先度）
        for beat in frontmatter_beats:
            key = (beat.episode, beat.scene, beat.source, beat.target, beat.emotion)
            merged[key] = beat
        
        # インラインを後から登録（既存キーならスキップ）
        for beat in inline_beats:
            key = (beat.episode, beat.scene, beat.source, beat.target, beat.emotion)
            if key in merged:
                conflicts.append((beat, merged[key]))
                logger.warning(
                    f"Beat conflict (frontmatter wins): {key} "
                    f"inline_delta={beat.delta} vs fm_delta={merged[key].delta}"
                )
            else:
                merged[key] = beat
        
        if conflicts:
            logger.info(f"Resolved {len(conflicts)} beat conflicts (frontmatter priority)")
        
        return list(merged.values())


def parse_script(script: str, episode: int, scene: int = 1, 
                 character_dict: Optional[set[str]] = None) -> ParsedScript:
    """便利関数: スクリプトをパースしてParsedScript返却"""
    parser = BeatParser(character_dict)
    return parser.parse_script(script, episode, scene)


__all__ = ["BeatParser", "parse_script"]