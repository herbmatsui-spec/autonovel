from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SpeechEmotion(str, Enum):
    NEUTRAL = "neutral"
    JOY = "joy"
    ANGER = "anger"
    SADNESS = "sadness"
    FEAR = "fear"
    SURPRISE = "surprise"
    WHISPER = "whisper"
    SHOUT = "shout"


@dataclass
class AcousticParameters:
    speed_scale: float = 1.0
    pitch_scale: float = 0.0
    intonation_scale: float = 1.0
    volume_scale: float = 1.0
    pause_after_sec: float = 0.4


EMOTION_ACOUSTIC_TABLE: dict[SpeechEmotion, AcousticParameters] = {
    SpeechEmotion.NEUTRAL: AcousticParameters(
        speed_scale=1.0,
        pitch_scale=0.0,
        intonation_scale=1.0,
        volume_scale=1.0,
        pause_after_sec=0.4,
    ),
    SpeechEmotion.JOY: AcousticParameters(
        speed_scale=1.15,
        pitch_scale=0.05,
        intonation_scale=1.2,
        volume_scale=1.1,
        pause_after_sec=0.3,
    ),
    SpeechEmotion.ANGER: AcousticParameters(
        speed_scale=1.25,
        pitch_scale=0.1,
        intonation_scale=1.4,
        volume_scale=1.3,
        pause_after_sec=0.2,
    ),
    SpeechEmotion.SADNESS: AcousticParameters(
        speed_scale=0.85,
        pitch_scale=-0.05,
        intonation_scale=0.7,
        volume_scale=0.8,
        pause_after_sec=0.6,
    ),
    SpeechEmotion.FEAR: AcousticParameters(
        speed_scale=1.1,
        pitch_scale=0.08,
        intonation_scale=1.3,
        volume_scale=0.9,
        pause_after_sec=0.3,
    ),
    SpeechEmotion.SURPRISE: AcousticParameters(
        speed_scale=1.2,
        pitch_scale=0.1,
        intonation_scale=1.5,
        volume_scale=1.2,
        pause_after_sec=0.3,
    ),
    SpeechEmotion.WHISPER: AcousticParameters(
        speed_scale=0.8,
        pitch_scale=-0.1,
        intonation_scale=0.5,
        volume_scale=0.4,
        pause_after_sec=0.5,
    ),
    SpeechEmotion.SHOUT: AcousticParameters(
        speed_scale=1.3,
        pitch_scale=0.15,
        intonation_scale=1.6,
        volume_scale=1.5,
        pause_after_sec=0.3,
    ),
}


class DialogueEmotionClassifier:
    """High-speed dialogue emotion classifier using keywords and punctuation."""

    EMOTION_KEYWORDS: dict[SpeechEmotion, list[str]] = {
        SpeechEmotion.JOY: ["笑", "わはは", "あはは", "うれし", "楽し", "最高", "やった", "ばんざい", "ニコニコ"],
        SpeechEmotion.ANGER: ["許さ", "殺", "死ね", "むかつ", "腹が立", "ふざけ", "絶対", "覚悟", "ぶん殴", "ムカつく"],
        SpeechEmotion.SADNESS: ["悲し", "泣", "涙", "辛い", "苦し", "寂し", "失望", "絶望", "後悔", "かなし"],
        SpeechEmotion.FEAR: ["怖", "恐ろし", "怯", "震え", "逃げ", "助け", "嫌だ", "こわい", "びくびく"],
        SpeechEmotion.SURPRISE: ["えっ", "なに", "まさか", "本当", "嘘", "驚", "信じられ", "マジで", "うそ"],
        SpeechEmotion.WHISPER: ["内緒", "ひそひそ", "小声", "こっそり", "秘密", "そっと", "内緒話"],
        SpeechEmotion.SHOUT: ["行くぞ", "負けるな", "立ち上がれ", "絶対に", "叫", "大声", "全力"],
    }

    def classify(self, text: str, context: str = "") -> SpeechEmotion:
        """Classify emotion from dialogue text and optional context."""
        combined = (context + " " + text).lower()

        # First, check explicit emotion keywords (highest priority)
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    # Special case: ANGER keywords with 3+ exclamation -> ANGER not SHOUT
                    if emotion == SpeechEmotion.ANGER and text.count("！") >= 3:
                        return SpeechEmotion.ANGER
                    # Special case: SHOUT keywords with 3+ exclamation -> SHOUT
                    if emotion == SpeechEmotion.SHOUT and text.count("！") >= 3:
                        return SpeechEmotion.SHOUT
                    return emotion

        # Check punctuation patterns
        exclamation_count = text.count("！")
        question_count = text.count("？") + text.count("?")
        ellipsis_count = text.count("…") + text.count("。。")
        
        # Surprise: ?! or ?! combination
        if "？" in text and "！" in text:
            return SpeechEmotion.SURPRISE
        if question_count >= 1:
            # Check if also has surprise keywords in context
            if any(kw in combined for kw in self.EMOTION_KEYWORDS[SpeechEmotion.SURPRISE]):
                return SpeechEmotion.SURPRISE
            return SpeechEmotion.SURPRISE

        # Ellipsis patterns
        if ellipsis_count >= 1:
            if any(kw in text for kw in self.EMOTION_KEYWORDS[SpeechEmotion.SADNESS]):
                return SpeechEmotion.SADNESS
            if any(kw in text for kw in ["辛", "苦", "寂", "失望", "後悔"]):
                return SpeechEmotion.SADNESS
            return SpeechEmotion.WHISPER

        # Exclamation marks
        if exclamation_count >= 3:
            if any(kw in text for kw in self.EMOTION_KEYWORDS[SpeechEmotion.SHOUT]):
                return SpeechEmotion.SHOUT
            if any(kw in text for kw in ["死", "殺", "許さ", "絶対", "覚悟"]):
                return SpeechEmotion.ANGER
            return SpeechEmotion.SHOUT
        
        if exclamation_count >= 2:
            if any(kw in text for kw in self.EMOTION_KEYWORDS[SpeechEmotion.ANGER]):
                return SpeechEmotion.ANGER
            if any(kw in text for kw in self.EMOTION_KEYWORDS[SpeechEmotion.SHOUT]):
                return SpeechEmotion.SHOUT
            return SpeechEmotion.JOY
        
        if exclamation_count == 1:
            if any(kw in text for kw in self.EMOTION_KEYWORDS[SpeechEmotion.SHOUT]):
                return SpeechEmotion.SHOUT
            if any(kw in text for kw in self.EMOTION_KEYWORDS[SpeechEmotion.ANGER]):
                return SpeechEmotion.ANGER
            return SpeechEmotion.JOY

        return SpeechEmotion.NEUTRAL

    def adjust_acoustics_by_punctuation(
        self, params: AcousticParameters, text: str
    ) -> AcousticParameters:
        """Dynamically adjust acoustic parameters based on punctuation."""
        adjusted = AcousticParameters(
            speed_scale=params.speed_scale,
            pitch_scale=params.pitch_scale,
            intonation_scale=params.intonation_scale,
            volume_scale=params.volume_scale,
            pause_after_sec=params.pause_after_sec,
        )

        exclamation_count = text.count("！")
        if exclamation_count >= 3:
            adjusted.speed_scale += 0.1
            adjusted.volume_scale += 0.1
            adjusted.intonation_scale += 0.1
        elif exclamation_count >= 2:
            adjusted.speed_scale += 0.05
            adjusted.volume_scale += 0.05

        if "？" in text or "?" in text:
            adjusted.pitch_scale += 0.03
            adjusted.intonation_scale += 0.1

        if "…" in text or "。。" in text:
            adjusted.pause_after_sec += 0.3
            adjusted.speed_scale *= 0.9

        return adjusted