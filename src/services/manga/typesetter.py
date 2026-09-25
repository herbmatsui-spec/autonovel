"""Optional Typesetting and Speech Bubble Renderer for Manga Sheets."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from src.services.manga.config import MangaPipelineConfig
from src.services.manga.models import SpeechBubble

logger = logging.getLogger(__name__)


class MangaTypesetter:
    """漫画シートにフキダシとセリフ（写植）をオーバーレイ合成するオプションレンダラー。"""

    def __init__(self, config: Optional[MangaPipelineConfig] = None):
        self.config = config or MangaPipelineConfig()

    def apply_typesetting(
        self,
        image_path: Path,
        dialogues: List[SpeechBubble],
        output_path: Optional[Path] = None,
    ) -> Path:
        """指定されたセリフリストを画像上の該当コマに写植する。"""
        if output_path is None:
            output_path = (
                image_path.parent.parent
                / "finalized"
                / f"typeset_{image_path.name}"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not dialogues:
            # セリフがない場合はそのままコピー
            output_path.write_bytes(image_path.read_bytes())
            return output_path

        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(image_path).convert("RGBA")
        width, height = img.size

        # 4列×6行のセルサイズ計算
        cols = self.config.grid_cols
        rows = self.config.grid_rows
        cell_w = width / cols
        cell_h = height / rows

        draw = ImageDraw.Draw(img)
        font = self._load_font(self.config.font_size)

        for bubble in dialogues:
            idx = bubble.panel_index
            if idx < 0 or idx >= (cols * rows):
                continue

            # コマの位置（行・列）
            col = idx % cols
            row = idx // cols

            panel_x0 = col * cell_w
            panel_y0 = row * cell_h

            # フキダシ中心位置
            center_x = panel_x0 + (bubble.rel_x * cell_w)
            center_y = panel_y0 + (bubble.rel_y * cell_h)

            # テキストサイズ測定
            bbox = draw.textbbox((0, 0), bubble.text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            pad_x = 16
            pad_y = 12
            bx0 = center_x - (text_w / 2) - pad_x
            by0 = center_y - (text_h / 2) - pad_y
            bx1 = center_x + (text_w / 2) + pad_x
            by1 = center_y + (text_h / 2) + pad_y

            # フキダシ描画（角丸長方形、白地＋黒枠）
            draw.rounded_rectangle(
                [bx0, by0, bx1, by1],
                radius=12,
                fill=(255, 255, 255, 240),
                outline=(0, 0, 0, 255),
                width=3,
            )

            # テキスト描画
            tx = center_x - (text_w / 2)
            ty = center_y - (text_h / 2)
            draw.text((tx, ty), bubble.text, fill=(0, 0, 0, 255), font=font)

        # RGBに変換して保存
        final_img = img.convert("RGB")
        final_img.save(output_path, format="PNG")
        logger.info("Typesetting applied successfully to: %s", output_path)
        return output_path

    def _load_font(self, size: int):
        """利用可能なフォントをロードする（Windows標準フォントまたはデフォルトフォント）。"""
        from PIL import ImageFont

        font_candidates = [
            self.config.default_font_name,
            "C:\\Windows\\Fonts\\msgothic.ttc",
            "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\yumin.ttf",
            "Arial.ttf",
        ]
        for font_path in font_candidates:
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                continue

        return ImageFont.load_default()
