"""API client for NanoBanana 2 Lite (Gemini 3.1 Flash-Lite Image)."""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import List, Optional

from src.services.manga.config import MangaPipelineConfig
from src.services.manga.models import CharacterReference

logger = logging.getLogger(__name__)


class NanoBananaClient:
    """NanoBanana 2 Lite (Gemini 3.1 Flash-Lite Image) API クライアント。"""

    def __init__(self, config: Optional[MangaPipelineConfig] = None, mock_mode: bool = False):
        self.config = config or MangaPipelineConfig()
        self.mock_mode = mock_mode or not bool(self.config.api_key)
        self.client = None

        if not self.mock_mode:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.config.api_key)
            except Exception as e:
                logger.warning("Could not initialize genai.Client (%s). Falling back to mock mode.", e)
                self.mock_mode = True

    def generate_sheet(
        self,
        prompt: str,
        negative_prompt: str = "",
        character_refs: Optional[List[CharacterReference]] = None,
        aspect_ratio: str = "3:4",
        output_path: Optional[Path] = None,
    ) -> Path:
        """1話分の24コマ漫画シート（1枚）を生成する。"""
        if output_path is None:
            ts = int(time.time() * 1000)
            output_path = self.config.output_base_dir / "raw_sheets" / f"sheet_{ts}.png"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.mock_mode:
            logger.info("[MockMode] Generating simulated 24-panel manga sheet at %s", output_path)
            self._generate_mock_sheet(output_path, aspect_ratio)
            return output_path

        # 実際の Gemini API 呼び出し
        try:
            from google.genai import types

            config_kwargs = {
                "number_of_images": 1,
                "aspect_ratio": aspect_ratio,
            }
            if negative_prompt:
                config_kwargs["negative_prompt"] = negative_prompt

            config = types.GenerateImagesConfig(**config_kwargs)
            response = self.client.models.generate_images(
                model=self.config.model_id,
                prompt=prompt,
                config=config,
            )

            if not response.generated_images:
                raise RuntimeError("No images returned from NanoBanana 2 Lite API.")

            image_bytes = response.generated_images[0].image.image_bytes
            with open(output_path, "wb") as f:
                f.write(image_bytes)

            logger.info("Successfully generated manga sheet: %s", output_path)
            return output_path

        except Exception as e:
            logger.error("NanoBanana 2 Lite API generation failed: %s", e)
            raise e

    def edit_sheet_panel(
        self,
        source_image_path: Path,
        edit_instruction: str,
        output_path: Optional[Path] = None,
    ) -> Path:
        """自然言語指示による部分修正（インペイント/リファイン）。"""
        if output_path is None:
            ts = int(time.time() * 1000)
            output_path = self.config.output_base_dir / "edited" / f"edited_{ts}.png"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.mock_mode:
            logger.info("[MockMode] Editing sheet panel at %s: %s", output_path, edit_instruction)
            # モックの場合はソース画像をコピーまたは微修正保存
            if source_image_path.exists():
                output_path.write_bytes(source_image_path.read_bytes())
            else:
                self._generate_mock_sheet(output_path)
            return output_path

        # 実APIの画像編集コール（Imagen/Gemini Image Editing）
        raise NotImplementedError("Live image editing requires active API key and genai SDK support.")

    def _generate_mock_sheet(self, output_path: Path, aspect_ratio: str = "3:4") -> None:
        """テストおよびローカル検証用のダミー24コマ漫画シート（PILで4x6グリッド描画）を生成する。"""
        try:
            from PIL import Image, ImageDraw

            # 3:4 比率 (768 x 1024)
            width, height = (768, 1024) if aspect_ratio == "3:4" else (1024, 1024)
            img = Image.new("L", (width, height), color=255)  # 白背景グレースケール
            draw = ImageDraw.Draw(img)

            # 4列×6行のグリッド描画
            cols = self.config.grid_cols
            rows = self.config.grid_rows
            cell_w = width / cols
            cell_h = height / rows

            for c in range(cols):
                for r in range(rows):
                    x0 = c * cell_w + 4
                    y0 = r * cell_h + 4
                    x1 = (c + 1) * cell_w - 4
                    y1 = (r + 1) * cell_h - 4
                    draw.rectangle([x0, y0, x1, y1], outline=0, width=2)
                    panel_idx = r * cols + c + 1
                    draw.text((x0 + 10, y0 + 10), f"P{panel_idx}", fill=100)

            img.save(output_path, format="PNG")
        except Exception as e:
            # PILがない場合のフォールバック（最小限のPNGヘッダ）
            logger.warning("PIL not available for mock sheet generation (%s). Writing raw placeholder.", e)
            output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
