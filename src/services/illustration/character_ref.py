"""キャラクター参照画像の管理。

生成前に「そのブックに出現するキャラクターの参照画像」を集め、
`ImageClientProtocol.generate(reference_images=...)` へ渡す。存在しない
キャラクターは静かにスキップする（黙って失敗させない）。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)


class CharacterReferenceManager:
    """参照画像の探索とキャッシュ。"""

    def __init__(self, ref_dir: Path | str = Path("static/character_refs")) -> None:
        self.ref_dir = Path(ref_dir)
        self._cache: dict[tuple[int, tuple[str, ...]], list[Path]] = {}

    @staticmethod
    def _normalize(name: str) -> str:
        return str(name).strip().replace("/", "_").replace("\\", "_")

    def path_for(self, book_id: int, name: str) -> Path:
        """特定のキャラクターの参照画像パス（存在可否は問わない）。"""
        return self.ref_dir / str(book_id) / f"{self._normalize(name)}.png"

    def get_references(
        self,
        book_id: int,
        characters: Optional[Sequence[str]] = None,
        use_cache: bool = True,
    ) -> List[Path]:
        """存在する参照画像のみを返す。"""
        names = tuple(sorted({self._normalize(c) for c in (characters or []) if str(c).strip()}))
        if not names:
            return []
        key = (book_id, names)
        if use_cache and key in self._cache:
            return list(self._cache[key])

        found = [p for p in (self.path_for(book_id, n) for n in names) if p.exists()]
        if not found:
            logger.debug("No character reference images found under %s", self.ref_dir)
        self._cache[key] = list(found)
        return found

    def register(self, book_id: int, name: str, image_path: Path) -> Path:
        """参照画像を所定位置へ保存（コピー）して登録する。"""
        source = Path(image_path)
        target = self.path_for(book_id, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            target.write_bytes(source.read_bytes())
        self._cache.clear()
        return target

    def clear_cache(self) -> None:
        self._cache.clear()


__all__ = ["CharacterReferenceManager"]
