"""統合イラスト生成向け写植（セリフ / フキダシ合成）。

`src/services/manga/typesetter.py` を一般化し、`SpeechBubble` dataclass に
依存せず dict でも受け取れるようにする。Pillow が無い環境では**元画像を
コピー**して縮退する。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# 候補フォント（Windows 標準 → 汎用）
_FONT_CANDIDATES = (
    "msgothic.ttc",
    "meiryo.ttc",
    "meiryo.ttf",
    "YuGothM.ttc",
    "NotoSansJP-Regular.otf",
    "Arial.ttf",
)


def _as_bubble_dict(bubble: Any) -> Dict[str, Any]:
    """`SpeechBubble` / dict を同じ形の dict に正規化する。"""
    if isinstance(bubble, dict):
        return {
            "panel_index": int(bubble.get("panel_index", 0)),
            "text": str(bubble.get("text", "")),
            "speaker": str(bubble.get("speaker", "")),
            "rel_x": float(bubble.get("rel_x", 0.5)),
            "rel_y": float(bubble.get("rel_y", 0.5)),
            "bubble_type": str(bubble.get("bubble_type", "normal")),
        }
    return {
        "panel_index": int(getattr(bubble, "panel_index", 0)),
        "text": str(getattr(bubble, "text", "")),
        "speaker": str(getattr(bubble, "speaker", "")),
        "rel_x": float(getattr(bubble, "rel_x", 0.5)),
        "rel_y": float(getattr(bubble, "rel_y", 0.5)),
        "bubble_type": str(getattr(bubble, "bubble_type", "normal")),
    }


class Typesetter:
    """生成画像へセリフを合成する（オプション機能）。"""

    def __init__(
        self,
        grid_cols: int = 4,
        grid_rows: int = 6,
        font_size: int = 24,
        default_font_name: str = "msgothic.ttc",
    ) -> None:
        self.grid_cols = max(1, int(grid_cols))
        self.grid_rows = max(1, int(grid_rows))
        self.font_size = max(8, int(font_size))
        self.default_font_name = default_font_name

    def apply(
        self,
        image_path: Path,
        dialogues: Optional[Sequence[Any]],
        output_path: Optional[Path] = None,
    ) -> Path:
        """セリフを合成した画像を書き出す。セリフ無し/Pillow 不在時はコピーを返す。"""
        input_path = Path(image_path)
        if output_path is None:
            output_path = input_path.parent / f"typeset_{input_path.name}"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bubbles: List[Dict[str, Any]] = [
            _as_bubble_dict(b) for b in (dialogues or [])
        ]
        bubbles = [b for b in bubbles if b["text"]]

        if not bubbles:
            output_path.write_bytes(input_path.read_bytes())
            return output_path

        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pillow unavailable; typesetting skipped (%s).", exc)
            output_path.write_bytes(input_path.read_bytes())
            return output_path

        try:
            with Image.open(input_path) as img:
                canvas = img.convert("RGBA")
            width, height = canvas.size
            cell_w = width / self.grid_cols
            cell_h = height / self.grid_rows
            draw = ImageDraw.Draw(canvas)
            font = self._load_font(ImageFont)

            total = self.grid_cols * self.grid_rows
            for bubble in bubbles:
                idx = bubble["panel_index"]
                if idx < 0 or idx >= total:
                    continue
                col = idx % self.grid_cols
                row = idx // self.grid_cols
                center_x = col * cell_w + bubble["rel_x"] * cell_w
                center_y = row * cell_h + bubble["rel_y"] * cell_h

                bbox = draw.textbbox((0, 0), bubble["text"], font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                pad_x, pad_y = 16, 12
                draw.rounded_rectangle(
                    [
                        center_x - text_w / 2 - pad_x,
                        center_y - text_h / 2 - pad_y,
                        center_x + text_w / 2 + pad_x,
                        center_y + text_h / 2 + pad_y,
                    ],
                    radius=12,
                    fill=(255, 255, 255, 240),
                    outline=(0, 0, 0, 255),
                    width=3,
                )
                draw.text(
                    (center_x - text_w / 2, center_y - text_h / 2),
                    bubble["text"],
                    fill=(0, 0, 0, 255),
                    font=font,
                )

            canvas.convert("RGB").save(output_path, format="PNG")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Typesetting failed (%s). Copying original.", exc)
            output_path.write_bytes(input_path.read_bytes())

        return output_path

    def _load_font(self, imagefont_module: Any) -> Any:
        for name in (self.default_font_name, *_FONT_CANDIDATES):
            try:
                return imagefont_module.truetype(name, size=self.font_size)
            except Exception:  # noqa: BLE001
                continue
        for name in _FONT_CANDIDATES:
            try:
                return imagefont_module.truetype(
                    str(Path("C:/Windows/Fonts") / name), size=self.font_size
                )
            except Exception:  # noqa: BLE001
                continue
        return imagefont_module.load_default()


__all__ = ["Typesetter"]
