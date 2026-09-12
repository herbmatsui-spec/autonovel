from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from src.services.audio.emotion_classifier import (
    AcousticParameters,
    SpeechEmotion,
    EMOTION_ACOUSTIC_TABLE,
)


VOICEVOX_STYLE_REGISTRY: dict[str, dict[SpeechEmotion, int]] = {
    "ずんだもん": {
        SpeechEmotion.NEUTRAL: 3,
        SpeechEmotion.JOY: 1,
        SpeechEmotion.ANGER: 7,
        SpeechEmotion.SADNESS: 5,
        SpeechEmotion.FEAR: 22,
        SpeechEmotion.SURPRISE: 22,
        SpeechEmotion.WHISPER: 22,
        SpeechEmotion.SHOUT: 7,
    },
    "四国めたん": {
        SpeechEmotion.NEUTRAL: 2,
        SpeechEmotion.JOY: 0,
        SpeechEmotion.ANGER: 6,
        SpeechEmotion.SADNESS: 4,
        SpeechEmotion.FEAR: 36,
        SpeechEmotion.SURPRISE: 36,
        SpeechEmotion.WHISPER: 36,
        SpeechEmotion.SHOUT: 6,
    },
    "春日部つむぎ": {
        SpeechEmotion.NEUTRAL: 8,
        SpeechEmotion.JOY: 9,
        SpeechEmotion.ANGER: 10,
        SpeechEmotion.SADNESS: 11,
        SpeechEmotion.FEAR: 12,
        SpeechEmotion.SURPRISE: 12,
        SpeechEmotion.WHISPER: 11,
        SpeechEmotion.SHOUT: 10,
    },
    "雨晴はう": {
        SpeechEmotion.NEUTRAL: 13,
        SpeechEmotion.JOY: 14,
        SpeechEmotion.ANGER: 15,
        SpeechEmotion.SADNESS: 16,
        SpeechEmotion.FEAR: 17,
        SpeechEmotion.SURPRISE: 17,
        SpeechEmotion.WHISPER: 16,
        SpeechEmotion.SHOUT: 15,
    },
    "波音リツ": {
        SpeechEmotion.NEUTRAL: 18,
        SpeechEmotion.JOY: 19,
        SpeechEmotion.ANGER: 20,
        SpeechEmotion.SADNESS: 21,
        SpeechEmotion.FEAR: 22,
        SpeechEmotion.SURPRISE: 22,
        SpeechEmotion.WHISPER: 21,
        SpeechEmotion.SHOUT: 20,
    },
    "玄野武宏": {
        SpeechEmotion.NEUTRAL: 23,
        SpeechEmotion.JOY: 24,
        SpeechEmotion.ANGER: 25,
        SpeechEmotion.SADNESS: 26,
        SpeechEmotion.FEAR: 27,
        SpeechEmotion.SURPRISE: 27,
        SpeechEmotion.WHISPER: 26,
        SpeechEmotion.SHOUT: 25,
    },
    "白上虎太郎": {
        SpeechEmotion.NEUTRAL: 28,
        SpeechEmotion.JOY: 29,
        SpeechEmotion.ANGER: 30,
        SpeechEmotion.SADNESS: 31,
        SpeechEmotion.FEAR: 32,
        SpeechEmotion.SURPRISE: 32,
        SpeechEmotion.WHISPER: 31,
        SpeechEmotion.SHOUT: 30,
    },
    "青山龍星": {
        SpeechEmotion.NEUTRAL: 33,
        SpeechEmotion.JOY: 34,
        SpeechEmotion.ANGER: 35,
        SpeechEmotion.SADNESS: 36,
        SpeechEmotion.FEAR: 37,
        SpeechEmotion.SURPRISE: 37,
        SpeechEmotion.WHISPER: 36,
        SpeechEmotion.SHOUT: 35,
    },
    "冥鳴ひまり": {
        SpeechEmotion.NEUTRAL: 38,
        SpeechEmotion.JOY: 39,
        SpeechEmotion.ANGER: 40,
        SpeechEmotion.SADNESS: 41,
        SpeechEmotion.FEAR: 42,
        SpeechEmotion.SURPRISE: 42,
        SpeechEmotion.WHISPER: 41,
        SpeechEmotion.SHOUT: 40,
    },
    "九州そら": {
        SpeechEmotion.NEUTRAL: 43,
        SpeechEmotion.JOY: 44,
        SpeechEmotion.ANGER: 45,
        SpeechEmotion.SADNESS: 46,
        SpeechEmotion.FEAR: 47,
        SpeechEmotion.SURPRISE: 47,
        SpeechEmotion.WHISPER: 46,
        SpeechEmotion.SHOUT: 45,
    },
    "もち子": {
        SpeechEmotion.NEUTRAL: 48,
        SpeechEmotion.JOY: 49,
        SpeechEmotion.ANGER: 50,
        SpeechEmotion.SADNESS: 51,
        SpeechEmotion.FEAR: 52,
        SpeechEmotion.SURPRISE: 52,
        SpeechEmotion.WHISPER: 51,
        SpeechEmotion.SHOUT: 50,
    },
    "剣崎雛": {
        SpeechEmotion.NEUTRAL: 53,
        SpeechEmotion.JOY: 54,
        SpeechEmotion.ANGER: 55,
        SpeechEmotion.SADNESS: 56,
        SpeechEmotion.FEAR: 57,
        SpeechEmotion.SURPRISE: 57,
        SpeechEmotion.WHISPER: 56,
        SpeechEmotion.SHOUT: 55,
    },
    "WhiteCUL": {
        SpeechEmotion.NEUTRAL: 58,
        SpeechEmotion.JOY: 59,
        SpeechEmotion.ANGER: 60,
        SpeechEmotion.SADNESS: 61,
        SpeechEmotion.FEAR: 62,
        SpeechEmotion.SURPRISE: 62,
        SpeechEmotion.WHISPER: 61,
        SpeechEmotion.SHOUT: 60,
    },
    "後鬼": {
        SpeechEmotion.NEUTRAL: 63,
        SpeechEmotion.JOY: 64,
        SpeechEmotion.ANGER: 65,
        SpeechEmotion.SADNESS: 66,
        SpeechEmotion.FEAR: 67,
        SpeechEmotion.SURPRISE: 67,
        SpeechEmotion.WHISPER: 66,
        SpeechEmotion.SHOUT: 65,
    },
    "No.7": {
        SpeechEmotion.NEUTRAL: 68,
        SpeechEmotion.JOY: 69,
        SpeechEmotion.ANGER: 70,
        SpeechEmotion.SADNESS: 71,
        SpeechEmotion.FEAR: 72,
        SpeechEmotion.SURPRISE: 72,
        SpeechEmotion.WHISPER: 71,
        SpeechEmotion.SHOUT: 70,
    },
    "ちび式じい": {
        SpeechEmotion.NEUTRAL: 73,
        SpeechEmotion.JOY: 74,
        SpeechEmotion.ANGER: 75,
        SpeechEmotion.SADNESS: 76,
        SpeechEmotion.FEAR: 77,
        SpeechEmotion.SURPRISE: 77,
        SpeechEmotion.WHISPER: 76,
        SpeechEmotion.SHOUT: 75,
    },
    "櫻歌ミコ": {
        SpeechEmotion.NEUTRAL: 78,
        SpeechEmotion.JOY: 79,
        SpeechEmotion.ANGER: 80,
        SpeechEmotion.SADNESS: 81,
        SpeechEmotion.FEAR: 82,
        SpeechEmotion.SURPRISE: 82,
        SpeechEmotion.WHISPER: 81,
        SpeechEmotion.SHOUT: 80,
    },
    "小夜/SAYO": {
        SpeechEmotion.NEUTRAL: 83,
        SpeechEmotion.JOY: 84,
        SpeechEmotion.ANGER: 85,
        SpeechEmotion.SADNESS: 86,
        SpeechEmotion.FEAR: 87,
        SpeechEmotion.SURPRISE: 87,
        SpeechEmotion.WHISPER: 86,
        SpeechEmotion.SHOUT: 85,
    },
    "ナースロボ＿タイプＴ": {
        SpeechEmotion.NEUTRAL: 88,
        SpeechEmotion.JOY: 89,
        SpeechEmotion.ANGER: 90,
        SpeechEmotion.SADNESS: 91,
        SpeechEmotion.FEAR: 92,
        SpeechEmotion.SURPRISE: 92,
        SpeechEmotion.WHISPER: 91,
        SpeechEmotion.SHOUT: 90,
    },
    "†聖騎士 紅桜†": {
        SpeechEmotion.NEUTRAL: 93,
        SpeechEmotion.JOY: 94,
        SpeechEmotion.ANGER: 95,
        SpeechEmotion.SADNESS: 96,
        SpeechEmotion.FEAR: 97,
        SpeechEmotion.SURPRISE: 97,
        SpeechEmotion.WHISPER: 96,
        SpeechEmotion.SHOUT: 95,
    },
    "雀松朱司": {
        SpeechEmotion.NEUTRAL: 98,
        SpeechEmotion.JOY: 99,
        SpeechEmotion.ANGER: 100,
        SpeechEmotion.SADNESS: 101,
        SpeechEmotion.FEAR: 102,
        SpeechEmotion.SURPRISE: 102,
        SpeechEmotion.WHISPER: 101,
        SpeechEmotion.SHOUT: 100,
    },
    "麒ヶ島宗麟": {
        SpeechEmotion.NEUTRAL: 103,
        SpeechEmotion.JOY: 104,
        SpeechEmotion.ANGER: 105,
        SpeechEmotion.SADNESS: 106,
        SpeechEmotion.FEAR: 107,
        SpeechEmotion.SURPRISE: 107,
        SpeechEmotion.WHISPER: 106,
        SpeechEmotion.SHOUT: 105,
    },
    "裏命": {
        SpeechEmotion.NEUTRAL: 108,
        SpeechEmotion.JOY: 109,
        SpeechEmotion.ANGER: 110,
        SpeechEmotion.SADNESS: 111,
        SpeechEmotion.FEAR: 112,
        SpeechEmotion.SURPRISE: 112,
        SpeechEmotion.WHISPER: 111,
        SpeechEmotion.SHOUT: 110,
    },
    "先生": {
        SpeechEmotion.NEUTRAL: 113,
        SpeechEmotion.JOY: 114,
        SpeechEmotion.ANGER: 115,
        SpeechEmotion.SADNESS: 116,
        SpeechEmotion.FEAR: 117,
        SpeechEmotion.SURPRISE: 117,
        SpeechEmotion.WHISPER: 116,
        SpeechEmotion.SHOUT: 115,
    },
    "栗田まろん": {
        SpeechEmotion.NEUTRAL: 118,
        SpeechEmotion.JOY: 119,
        SpeechEmotion.ANGER: 120,
        SpeechEmotion.SADNESS: 121,
        SpeechEmotion.FEAR: 122,
        SpeechEmotion.SURPRISE: 122,
        SpeechEmotion.WHISPER: 121,
        SpeechEmotion.SHOUT: 120,
    },
    "あいえるたん": {
        SpeechEmotion.NEUTRAL: 123,
        SpeechEmotion.JOY: 124,
        SpeechEmotion.ANGER: 125,
        SpeechEmotion.SADNESS: 126,
        SpeechEmotion.FEAR: 127,
        SpeechEmotion.SURPRISE: 127,
        SpeechEmotion.WHISPER: 126,
        SpeechEmotion.SHOUT: 125,
    },
    "詩歌": {
        SpeechEmotion.NEUTRAL: 128,
        SpeechEmotion.JOY: 129,
        SpeechEmotion.ANGER: 130,
        SpeechEmotion.SADNESS: 131,
        SpeechEmotion.FEAR: 132,
        SpeechEmotion.SURPRISE: 132,
        SpeechEmotion.WHISPER: 131,
        SpeechEmotion.SHOUT: 130,
    },
}


@dataclass
class SpeakerConfig:
    name: str
    gender: str = "female"
    role: str = "heroine"
    default_style_id: int = 3


def resolve_speaker_and_style(
    speaker_name: str,
    emotion: SpeechEmotion,
    gender: str = "female",
    role: str = "heroine",
) -> tuple[int, AcousticParameters]:
    """
    Resolve VOICEVOX speaker_id (style_id) and acoustic parameters for a character and emotion.
    
    Returns:
        tuple of (speaker_id, AcousticParameters)
    """
    # Get base acoustic parameters for the emotion
    base_params = EMOTION_ACOUSTIC_TABLE.get(emotion, EMOTION_ACOUSTIC_TABLE[SpeechEmotion.NEUTRAL])
    
    # Look up style registry for the speaker
    speaker_styles = VOICEVOX_STYLE_REGISTRY.get(speaker_name)
    
    if speaker_styles is not None:
        # Speaker found in registry
        style_id = speaker_styles.get(emotion)
        if style_id is not None:
            return style_id, base_params
        
        # Emotion-specific style not found, try NEUTRAL
        style_id = speaker_styles.get(SpeechEmotion.NEUTRAL)
        if style_id is not None:
            return style_id, base_params
        
        # Fallback to first available style for this speaker
        style_id = next(iter(speaker_styles.values()))
        return style_id, base_params
    
    # Speaker not in registry - use default based on gender/role
    default_id = _get_default_speaker_id(gender, role)
    return default_id, base_params


def assign_speaker_id(speaker_name: str, gender: str = "female", role: str = "heroine") -> int:
    """Legacy wrapper for speaker ID assignment."""
    if speaker_name == "narration":
        return 3
    # Use existing internal helper
    return _get_default_speaker_id(gender, role)


def _get_default_speaker_id(gender: str, role: str) -> int:
    """Get default VOICEVOX speaker ID based on gender and role."""
    # Default to ずんだもん (neutral female)
    if gender == "male":
        if role == "hero":
            return 23  # 玄野武宏 (normal)
        elif role == "villain":
            return 28  # 青山龍星 (normal)
        return 23  # default male
    
    # Female defaults
    if role == "heroine":
        return 3  # ずんだもん (normal)
    elif role == "villain":
        return 38  # 冥鳴ひまり (normal)
    elif role == "child":
        return 13  # 雨晴はう (normal)
    return 3  # default to ずんだもん


def load_voice_config(config_path: Optional[str] = None) -> dict[str, dict[SpeechEmotion, int]]:
    """
    Load VOICEVOX style configuration from YAML file.
    
    Expected YAML format:
    speakers:
      "Character Name":
        neutral: 3
        joy: 1
        anger: 7
        ...
    
    Args:
        config_path: Path to YAML config file. If None, tries to load from
                     config/audio_voices.yaml relative to project root.
    
    Returns:
        Dictionary mapping speaker names to emotion->style_id mappings.
    """
    if config_path is None:
        # Try to find config file
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / "audio_voices.yaml"
    
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data or "speakers" not in data:
            return {}
        
        result: dict[str, dict[SpeechEmotion, int]] = {}
        for speaker_name, styles in data["speakers"].items():
            result[speaker_name] = {}
            for emotion_str, style_id in styles.items():
                try:
                    emotion = SpeechEmotion(emotion_str)
                    result[speaker_name][emotion] = int(style_id)
                except ValueError:
                    continue
        
        return result
    except Exception:
        return {}


def get_speaker_config(speaker_name: str) -> SpeakerConfig:
    """Get speaker configuration (gender, role, default style)."""
    # This could be extended to load from a config file
    male_speakers = {"玄野武宏", "白上虎太郎", "青山龍星", "雀松朱司", "麒ヶ島宗麟", "裏命", "先生"}
    child_speakers = {"雨晴はう", "もち子", "あいえるたん"}
    villain_speakers = {"冥鳴ひまり", "†聖騎士 紅桜†"}
    
    if speaker_name in male_speakers:
        return SpeakerConfig(name=speaker_name, gender="male", role="hero")
    elif speaker_name in child_speakers:
        return SpeakerConfig(name=speaker_name, gender="female", role="child")
    elif speaker_name in villain_speakers:
        return SpeakerConfig(name=speaker_name, gender="female", role="villain")
    
    return SpeakerConfig(name=speaker_name, gender="female", role="heroine")