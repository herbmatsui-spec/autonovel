"""Character voice profile models and prompt customization."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VoiceProfile:
    """キャラクターごとの口調・内心表出度などのプロファイル"""
    character_name: str
    speech_patterns: List[str] = field(default_factory=list)
    vocabulary_level: str = "standard"  # casual, formal, archaic, child, etc.
    emotional_leakage: float = 0.5      # 0.0: ポーカーフェイス, 1.0: 感情が顔や声に丸出し
    lying_tendency: float = 0.1         # 虚飾・嘘をつきやすさ

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_name": self.character_name,
            "speech_patterns": list(self.speech_patterns),
            "vocabulary_level": self.vocabulary_level,
            "emotional_leakage": self.emotional_leakage,
            "lying_tendency": self.lying_tendency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VoiceProfile:
        return cls(
            character_name=str(data["character_name"]),
            speech_patterns=list(data.get("speech_patterns", [])),
            vocabulary_level=str(data.get("vocabulary_level", "standard")),
            emotional_leakage=float(data.get("emotional_leakage", 0.5)),
            lying_tendency=float(data.get("lying_tendency", 0.1)),
        )

    def render_instruction(self) -> str:
        """プロンプト注入用の指示文を生成"""
        leak_desc = "内心をほとんど表情に出さない" if self.emotional_leakage < 0.3 else "感情が言動に素直に表れる"
        patterns = "、".join(self.speech_patterns) if self.speech_patterns else "特になし"
        return (
            f"【{self.character_name}の台詞・描写特徴】\n"
            f"- 口調特徴: {patterns}\n"
            f"- 語彙レベル: {self.vocabulary_level}\n"
            f"- 感情の表出度: {leak_desc} (leakage={self.emotional_leakage})\n"
        )


__all__ = ["VoiceProfile"]
