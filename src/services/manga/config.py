"""Configuration for NanoBanana 2 Lite (Gemini 3.1 Flash-Lite Image) Manga Pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MangaPipelineConfig:
    """マンガ生成パイプライン設定。"""
    # モデル設定
    model_id: str = "gemini-3.1-flash-lite-image"
    api_key: str = ""
    cost_per_image_usd: float = 0.034
    
    # グリッド設定（24コマ: 4列×6行）
    grid_cols: int = 4
    grid_rows: int = 6
    total_panels: int = 24
    
    # 出力パス設定
    output_base_dir: Path = Path("output/manga")
    char_ref_dir: Path = Path("data/manga/char_ref")
    
    # 超解像設定
    upscale_factor: int = 4
    target_upscale_width: int = 4096
    use_gpu_upscaler: bool = True
    
    # 写植設定（オプション）
    enable_typesetting: bool = False
    default_font_name: str = "msgothic.ttc"  # Windows標準フォント
    font_size: int = 24

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = (
                os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_GENAI_API_KEY")
                or os.getenv("NANOBANANA_API_KEY")
                or ""
            )
        self.output_base_dir = Path(self.output_base_dir)
        self.char_ref_dir = Path(self.char_ref_dir)
