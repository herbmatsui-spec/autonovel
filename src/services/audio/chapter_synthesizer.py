import asyncio
import logging
from collections import Counter
from src.services.audio.audio_combiner import AudioCombiner
from src.services.audio.audio_storage import AudioStorageService
from src.services.audio.base import AudioSynthesisClient, AudioSynthesisRequest
from src.services.audio.dialogue_extractor import DialogueExtractor
from src.services.audio.factory import get_audio_client
from src.services.audio.speaker_mapper import resolve_speaker_and_style

logger = logging.getLogger(__name__)


class ChapterAudioSynthesizer:
    """1章分のテキストを受け取り、抽出・合成・結合・保存を一貫して行うオーケストレータ (Step 15)。"""

    def __init__(
        self,
        audio_client: AudioSynthesisClient | None = None,
        storage_service: AudioStorageService | None = None,
        max_concurrent: int = 4,
    ):
        self.client = audio_client or get_audio_client()
        self.storage = storage_service or AudioStorageService()
        self.extractor = DialogueExtractor()
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def synthesize_chapter(
        self,
        book_id: int,
        episode_num: int,
        chapter_text: str,
        characters: list[str] | None = None,
        character_details: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, any]:
        """チャプターを音声合成して永続化し、メタデータを返す。"""
        lines = self.extractor.extract_lines(chapter_text, characters=characters)
        if not lines:
            return {
                "file_path": "",
                "duration_seconds": 0.0,
                "lines_count": 0,
                "emotion_distribution": {},
            }

        details = character_details or {}
        
        # 並列合成
        clips = await self._synthesize_lines_parallel(lines, details)
        
        # ポーズ時間計算
        pauses = [line.acoustics.pause_after_sec for line in lines if line.acoustics][:-1]
        
        # 全クリップを可変ポーズで結合
        combined_wav = AudioCombiner.combine_wav_clips(clips, pauses=pauses)
        
        # 保存
        saved_path = self.storage.save_chapter_audio(book_id, episode_num, combined_wav)

        # 感情分布集計
        emotion_dist = self._calculate_emotion_distribution(lines)

        # Duration calculation from lines' acoustics
        total_duration = sum(line.acoustics.pause_after_sec + 0.5 for line in lines if line.acoustics)

        return {
            "file_path": saved_path,
            "duration_seconds": total_duration,
            "lines_count": len(lines),
            "file_size_bytes": len(combined_wav),
            "emotion_distribution": emotion_dist,
        }

    async def _synthesize_lines_parallel(
        self,
        lines: list,
        character_details: dict[str, dict[str, str]],
    ) -> list:
        """セリフ行を並列で合成 (Step 43)"""
        async def synthesize_line(line):
            async with self.semaphore:
                return await self._synthesize_single_line(line, character_details)

        tasks = [synthesize_line(line) for line in lines]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        clips = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Failed to synthesize line %d: %s", lines[i].line_index, result)
                clips.append(None)
            elif result is not None and result.audio_bytes:
                clips.append(result.audio_bytes)
            else:
                clips.append(None)
        
        # Noneを除外
        return [c for c in clips if c is not None]

    async def _synthesize_single_line(
        self,
        line,
        character_details: dict[str, dict[str, str]],
    ):
        """単一セリフ行の合成 (感情連動パラメータ適用)"""
        # 話者ID・スタイルID決定 (感情連動)
        if line.is_dialogue:
            char_info = character_details.get(line.speaker_name, {})
            gender = char_info.get("gender", "female")
            role = char_info.get("role", "heroine")
            speaker_id, acoustics = resolve_speaker_and_style(
                line.speaker_name, line.emotion, gender=gender, role=role
            )
        else:
            speaker_id, acoustics = resolve_speaker_and_style(
                "narration", line.emotion, gender="female", role="narrator"
            )

        req = AudioSynthesisRequest(
            text=line.text,
            speaker_id=speaker_id,
            speed_scale=acoustics.speed_scale,
            pitch_scale=acoustics.pitch_scale,
            intonation_scale=acoustics.intonation_scale,
            volume_scale=acoustics.volume_scale,
        )
        
        res = await self.client.synthesize(req)
        return res

    def _calculate_emotion_distribution(self, lines: list) -> dict[str, float]:
        """感情分布をパーセンテージで計算 (Step 45)"""
        if not lines:
            return {}
        
        emotion_counts = Counter(line.emotion.value for line in lines)
        total = len(lines)
        return {
            emotion: round(count / total * 100, 1)
            for emotion, count in emotion_counts.items()
        }