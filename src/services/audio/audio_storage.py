from pathlib import Path
from src.backend.config import settings


class AudioStorageService:
    """音声ファイルの永続化・パス管理を行うサービス (Step 13)。"""

    def __init__(self, base_dir: str | Path | None = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            multimedia_dir = getattr(settings, "MULTIMEDIA_OUTPUT_DIR", "storage/multimedia")
            self.base_dir = Path(multimedia_dir) / "audio"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_chapter_audio_path(self, book_id: int, episode_num: int) -> Path:
        book_dir = self.base_dir / str(book_id)
        book_dir.mkdir(parents=True, exist_ok=True)
        return book_dir / f"ep_{episode_num}_full.wav"

    def save_chapter_audio(self, book_id: int, episode_num: int, audio_bytes: bytes) -> str:
        dest_path = self.get_chapter_audio_path(book_id, episode_num)
        dest_path.write_bytes(audio_bytes)
        return str(dest_path)

    def get_audio_clip_path(self, book_id: int, episode_num: int, line_index: int) -> Path:
        clip_dir = self.base_dir / str(book_id) / "clips"
        clip_dir.mkdir(parents=True, exist_ok=True)
        return clip_dir / f"ep_{episode_num}_{line_index}.wav"

    def save_audio_clip(self, book_id: int, episode_num: int, line_index: int, audio_bytes: bytes) -> str:
        dest_path = self.get_audio_clip_path(book_id, episode_num, line_index)
        dest_path.write_bytes(audio_bytes)
        return str(dest_path)
