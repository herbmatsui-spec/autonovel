import re
from dataclasses import dataclass
from typing import Optional

from src.services.audio.emotion_classifier import (
    AcousticParameters,
    DialogueEmotionClassifier,
    SpeechEmotion,
)


@dataclass
class DialogueLine:
    """小説本文から抽出された発話・地の文行"""

    line_index: int
    text: str
    is_dialogue: bool
    speaker_name: str = "narration"
    speaker_id: int = 3
    emotion: SpeechEmotion = SpeechEmotion.NEUTRAL
    acoustics: Optional[AcousticParameters] = None


def split_long_sentence(text: str, max_length: int = 120) -> list[str]:
    """VOICEVOXのバッファ溢れ防止のため、長文を句読点境界で安全に分割する (Step 10)。"""
    text = text.strip()
    if len(text) <= max_length:
        return [text] if text else []

    # 句読点（。！？!?）で区切る
    chunks: list[str] = []
    current = ""
    # 区切り文字を保持しながら分割
    tokens = re.split(r"([。！？!?]+)", text)
    for i in range(0, len(tokens), 2):
        sentence = tokens[i]
        punct = tokens[i + 1] if i + 1 < len(tokens) else ""
        part = sentence + punct
        if not part:
            continue
        if len(current) + len(part) <= max_length:
            current += part
        else:
            if current:
                chunks.append(current)
            if len(part) > max_length:
                # 読点（、,）でも分割
                sub_tokens = re.split(r"([、,]+)", part)
                sub_current = ""
                for j in range(0, len(sub_tokens), 2):
                    sub_s = sub_tokens[j]
                    sub_p = sub_tokens[j + 1] if j + 1 < len(sub_tokens) else ""
                    sub_part = sub_s + sub_p
                    if len(sub_current) + len(sub_part) <= max_length:
                        sub_current += sub_part
                    else:
                        if sub_current:
                            chunks.append(sub_current)
                        sub_current = sub_part
                if sub_current:
                    chunks.append(sub_current)
                current = ""
            else:
                current = part
    if current:
        chunks.append(current)
    return chunks


class DialogueExtractor:
    """本文からセリフ・地の文を分離し、文脈から話者を推定するパーサー (Steps 6, 7, 8, 10)。"""

    # かぎ括弧のパターン: 「...」 または 『...』
    DIALOGUE_PATTERN = re.compile(r"([「『].*?[」』])")

    def __init__(
        self,
        default_narrator_speaker_id: int = 3,
        emotion_classifier: Optional[DialogueEmotionClassifier] = None,
    ):
        self.default_narrator_speaker_id = default_narrator_speaker_id
        self.emotion_classifier = emotion_classifier or DialogueEmotionClassifier()

    def extract_lines(
        self,
        chapter_text: str,
        characters: list[str] | None = None,
        max_chunk_length: int = 120,
    ) -> list[DialogueLine]:
        """チャプター本文を行単位・セリフ単位に分解し、話者推定を行う。"""
        raw_paragraphs = [p.strip() for p in chapter_text.splitlines() if p.strip()]
        result: list[DialogueLine] = []
        line_idx = 0
        known_chars = characters or []
        last_mentioned_speaker = "speaker"

        for p in raw_paragraphs:
            # 括弧で区切る
            parts = self.DIALOGUE_PATTERN.split(p)
            for part in parts:
                part = part.strip()
                if not part:
                    continue

                is_dialogue = (part.startswith("「") and part.endswith("」")) or (
                    part.startswith("『") and part.endswith("』")
                )
                inner_text = part[1:-1].strip() if is_dialogue else part

                # 長文分割を適用
                sub_chunks = split_long_sentence(inner_text, max_length=max_chunk_length)
                for chunk in sub_chunks:
                    speaker = "narration"
                    if is_dialogue:
                        resolved = self._resolve_speaker(p, known_chars)
                        if resolved == "speaker" and last_mentioned_speaker != "speaker":
                            resolved = last_mentioned_speaker
                        speaker = resolved
                    else:
                        # 地の文から言及された登場人物をトラッキング
                        for char in known_chars:
                            if char in chunk:
                                last_mentioned_speaker = char
                                break

                    # 感情分類と音響パラメータ計算
                    emotion = self.emotion_classifier.classify(chunk, context=p)
                    acoustics = self.emotion_classifier.adjust_acoustics_by_punctuation(
                        self._get_base_acoustics(emotion), chunk
                    )

                    result.append(
                        DialogueLine(
                            line_index=line_idx,
                            text=chunk,
                            is_dialogue=is_dialogue,
                            speaker_name=speaker,
                            speaker_id=self.default_narrator_speaker_id,
                            emotion=emotion,
                            acoustics=acoustics,
                        )
                    )
                    line_idx += 1

        return result

    def _get_base_acoustics(self, emotion: SpeechEmotion) -> AcousticParameters:
        """感情に対応する基本音響パラメータを取得"""
        from src.services.audio.emotion_classifier import EMOTION_ACOUSTIC_TABLE
        return EMOTION_ACOUSTIC_TABLE.get(emotion, EMOTION_ACOUSTIC_TABLE[SpeechEmotion.NEUTRAL])

    def _resolve_speaker(self, paragraph: str, characters: list[str]) -> str:
        """段落内の文脈（〇〇は言った、〇〇が微笑んだ等）から話者を推定する (Step 8)。"""
        if not characters:
            return "speaker"

        for char in characters:
            # 「〇〇は〜」「〇〇が〜」「〇〇と〜」「〜と〇〇」「〜と呟く〇〇」
            pattern = rf"(?:{re.escape(char)}\s*[はがにと]|と\s*{re.escape(char)})"
            if re.search(pattern, paragraph):
                return char

        # 単純マッチング
        for char in characters:
            if char in paragraph:
                return char

        return "speaker"