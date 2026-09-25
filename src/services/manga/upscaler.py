"""Local super-resolution (upscaling) pipeline for manga sheets."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MangaUpscaler:
    """マンガシートを1Kから4K/8Kへ高解像度化するローカル超解像プロセッサ。"""

    def __init__(
        self,
        scale_factor: int = 4,
        target_width: int = 4096,
        executable_path: Optional[str] = None,
    ):
        self.scale_factor = scale_factor
        self.target_width = target_width
        self.executable_path = executable_path or shutil.which("realesrgan-ncnn-vulkan")

    def upscale(
        self,
        input_image_path: Path,
        output_image_path: Optional[Path] = None,
    ) -> Path:
        """マンガシートを高解像度化する。"""
        if output_image_path is None:
            output_image_path = (
                input_image_path.parent.parent
                / "upscaled"
                / f"upscaled_{input_image_path.name}"
            )

        output_image_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. 外部 Real-ESRGAN 実行ファイルがある場合はそちらを優先利用
        if self.executable_path and Path(self.executable_path).exists():
            success = self._run_external_realesrgan(input_image_path, output_image_path)
            if success:
                return output_image_path

        # 2. ローカル PIL 高品質超解像＋シャープネス補正（フォールバック）
        self._run_pil_super_resolution(input_image_path, output_image_path)
        return output_image_path

    def _run_external_realesrgan(self, input_path: Path, output_path: Path) -> bool:
        """realesrgan-ncnn-vulkan 等のバイナリを呼び出す。"""
        try:
            cmd = [
                self.executable_path,
                "-i", str(input_path),
                "-o", str(output_path),
                "-s", str(self.scale_factor),
                "-n", "realesrgan-x4plus-anime",
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=60)
            if res.returncode == 0 and output_path.exists():
                logger.info("External Real-ESRGAN upscaled successfully: %s", output_path)
                return True
        except Exception as e:
            logger.warning("External Real-ESRGAN failed (%s). Falling back to PIL.", e)
        return False

    def _run_pil_super_resolution(self, input_path: Path, output_path: Path) -> None:
        """PIL による Lanczos リサンプリング＋アンシャープマスクによる高精細化。"""
        from PIL import Image, ImageEnhance, ImageFilter

        img = Image.open(input_path)
        orig_w, orig_h = img.size

        new_w = max(orig_w * self.scale_factor, self.target_width)
        aspect = orig_h / orig_w
        new_h = int(new_w * aspect)

        # 高品質リサイズ (LANCZOS)
        upscaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # マンガ線画のコントラスト・エッジ強調
        enhancer = ImageEnhance.Contrast(upscaled)
        upscaled = enhancer.enhance(1.15)

        # アンシャープマスクで線画を引き締める
        upscaled = upscaled.filter(
            ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3)
        )

        upscaled.save(output_path, format="PNG")
        logger.info("PIL super-resolution completed: %s (%dx%d)", output_path, new_w, new_h)
