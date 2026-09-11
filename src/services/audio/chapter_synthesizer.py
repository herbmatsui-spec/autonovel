import logging
from src.services.audio.audio_combiner import AudioCombiner
from src.services.audio.audio_storage import AudioStorageService
from src.services.audio.base import AudioSynthesisClient, AudioSynthesisRequest
from src.services.audio.dialogue_extractor import DialogueExtractor
from src.services.audio.factory import get_audio_client
from src.services.audio.speaker_mapper import assign_speaker_id

logger = logging.getLogger(__name__)


class ChapterAudioSynthesizer:
    """1章分のテキストを受け取り、抽出・合成・結合・保存を一貫して行うオーケストレータ (Step 15)。"""

    def __init__(
        self,
        audio_client: AudioSynthesisClient | None = None,
        storage_service: AudioStorageService | None = None,
    ):
        self.client = audio_client or get_audio_client()
        self.storage = storage_service or AudioStorageService()
        self.extractor = DialogueExtractor()

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
            return {"file_path": "", "duration_seconds": 0.0, "lines_count": 0}

        details = character_details or {}
        clips: list[bytes] = []
        total_duration = 0.0

        for line in lines:
            # 話者ID決定
            if line.is_dialogue:
                char_info = details.get(line.speaker_name, {})
                gender = char_info.get("gender", "female")
                role = char_info.get("role", "heroine")
                speaker_id = assign_speaker_id(line.speaker_name, gender=gender, role=role)
            else:
                speaker_id = assign_speaker_id("narration")

            req = AudioSynthesisRequest(text=line.text, speaker_id=speaker_id)
            try:
                res = await self.client.synthesize(req)
                if res.audio_bytes:
                    clips.append(res.audio_bytes)
                    total_duration += res.duration_seconds
            except Exception as e:
                logger.warning("Failed to synthesize line %d: %s", line.line_index, e)

        # 全クリップを無音付きで結合
        combined_wav = AudioCombiner.combine_wav_clips(clips, silence_duration_sec=0.35)
        # 保存
        saved_path = self.storage.save_chapter_audio(book_id, episode_num, combined_wav)

        return {
            "file_path": saved_path,
            "duration_seconds": total_duration,
            "lines_count": len(lines),
            "file_size_bytes": len(combined_wav),
        }
