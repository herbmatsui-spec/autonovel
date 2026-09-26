"""統合イラスト生成向けローカル超解像。

`src/services/manga/upscaler.py` を一般化したもの。外部 Real-ESRGAN が
あればそれを使い、無ければ Pillow の Lanczos + アンシャープマスクで代替する。
Pillow も無い場合は**元画像をコピー**して縮退する（生成自体は成功扱い）。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Upscaler:
    """生成済み画像をローカルで高解像度化する。"""

    def __init__(
        self,
        scale_factor: int = 2,
        target_width: int = 2048,
        executable_path: Optional[str] = None,
    ) -> None:
        self.scale_factor = max(1, int(scale_factor))
        self.target_width = max(1, int(target_width))
        self.executable_path = executable_path or shutil.which("realesrgan-ncnn-vulkan")

    def upscale(
        self,
        input_image_path: Path,
        output_image_path: Optional[Path] = None,
    ) -> Path:
        """超解像する。失敗時は必ずパスを返す（呼び出し側が後段を続けられるよう）。"""
        input_path = Path(input_image_path)
        if output_image_path is None:
            output_image_path = input_path.parent / f"upscaled_{input_path.name}"
        output_image_path = Path(output_image_path)
        output_image_path.parent.mkdir(parents=True, exist_ok=True)

        if self.executable_path and Path(self.executable_path).exists():
            if self._run_external(input_path, output_image_path):
                return output_image_path

        try:
            self._run_pil(input_path, output_image_path)
            return output_image_path
        except Exception as exc:  # noqa: BLE001
            logger.warning("Super-resolution unavailable (%s). Copying original.", exc)
            output_image_path.write_bytes(input_path.read_bytes())
            return output_image_path

    def _run_external(self, input_path: Path, output_path: Path) -> bool:
        try:
            cmd = [
                str(self.executable_path),
                "-i", str(input_path),
                "-o", str(output_path),
                "-s", str(self.scale_factor),
                "-n", "realesrgan-x4plus-anime",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0 and output_path.exists():
                logger.info("External Real-ESRGAN upscaled: %s", output_path)
                return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("External Real-ESRGAN failed (%s). Falling back to PIL.", exc)
        return False

    def _run_pil(self, input_path: Path, output_path: Path) -> None:
        from PIL import Image, ImageEnhance, ImageFilter

        with Image.open(input_path) as img:
            orig_w, orig_h = img.size
            new_w = max(orig_w * self.scale_factor, self.target_width)
            new_h = max(1, int(new_w * (orig_h / max(1, orig_w))))
            upscaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            upscaled = ImageEnhance.Contrast(upscaled).enhance(1.15)
            upscaled = upscaled.filter(
                ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3)
            )
            upscaled.save(output_path, format="PNG")


__all__ = ["Upscaler"]
