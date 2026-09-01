"""挿絵（シーン）抽出・生成サービス。

本文から重要なシーンを抽出し、Imagen で挿絵を生成する。
シーン抽出は LLM を使う方式と、LLM がなくても動くヒューリスティック方式の
両方を用意し、低性能環境でも段階的に導入できる。
"""

import logging
import re
import time
from typing import List, Optional

from src.models.illustration import IllustrationRequest, IllustrationResult, IllustrationType
from src.services.illustration.model_selector import resolve_request_model
from src.services.illustration.prompts import apply_safety_modifier, build_scene_prompt
from src.services.image_service import ImageService

logger = logging.getLogger(__name__)


class SceneExtractor:
    """本文から挿絵にふさわしいシーン文を抽出する。"""

    # 視覚的要素を含むとみなす手がかり表現
    _VISUAL_CUES = [
        "見",
        "光",
        "空",
        "海",
        "山",
        "部屋",
        "目",
        "顔",
        "手",
        "風",
        "雪",
        "夜",
        "朝",
        "夕",
        "城",
        "街",
        "剣",
        "血",
        "花",
        "森",
        "川",
        "影",
        "炎",
        "窓",
    ]

    def extract_scenes(self, text: str, max_scenes: int = 3) -> List[str]:
        """ヒューリスティックでシーンを抽出する（LLM不要）。"""
        paragraphs = [p.strip() for p in re.split(r"\n{2,}|[。！？]\s*", text) if p.strip()]
        scored = []
        for p in paragraphs:
            if len(p) < 15:
                continue
            score = sum(1 for cue in self._VISUAL_CUES if cue in p)
            score += min(len(p), 300) / 100.0
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:max_scenes]]

    async def extract_scenes_with_llm(self, text: str, llm, max_scenes: int = 3) -> List[str]:
        """LLM を使ってシーンを抽出する。失敗時はヒューリスティックにフォールバック。"""
        prompt = (
            "以下の小説本文から、挿絵として視覚化するのにふさわしい"
            f"重要なシーンを最大{max_scenes}個抽出し、JSON配列で返してください。\n\n"
            f"{text[:2000]}"
        )
        try:
            resp = await llm.generate_json(
                model_name=getattr(llm, "default_model", "gemini-2.0-flash"),
                prompt=prompt,
                system_instruction="You are a scene extractor. Return only JSON array of strings.",
            )
            data = resp.metadata if hasattr(resp, "metadata") else resp
            if isinstance(data, dict):
                data = data.get("scenes", data.get("result", []))
            if isinstance(data, list):
                return [str(s) for s in data][:max_scenes]
        except Exception as e:  # noqa: BLE001
            logger.warning(f"LLM scene extraction failed, fallback to heuristic: {e}")
        return self.extract_scenes(text, max_scenes=max_scenes)


class SceneIllustrator:
    """抽出されたシーンから挿絵を生成する。"""

    def __init__(self, image_service: ImageService):
        self.image_service = image_service

    async def generate_for_scene(
        self, scene_text: str, request: IllustrationRequest
    ) -> IllustrationResult:
        start = time.time()
        prompt = build_scene_prompt(scene_text, request.book_context)
        prompt = apply_safety_modifier(prompt, request.safety_level, IllustrationType.EPISODE)

        image_url = await self.image_service.generate(
            prompt=prompt,
            model=resolve_request_model(request),
            aspect_ratio=request.aspect_ratio,
            safety_level=request.safety_level,
        )
        elapsed = int((time.time() - start) * 1000)
        return IllustrationResult(
            request=request,
            image_url=image_url,
            prompt=prompt,
            model_used=resolve_request_model(request),
            generation_time_ms=elapsed,
        )


class SceneIllustrationService:
    """シーン抽出と挿絵生成をまとめた高レベルサービス。"""

    def __init__(self, image_service: ImageService, llm: Optional[object] = None):
        self.extractor = SceneExtractor()
        self.illustrator = SceneIllustrator(image_service)
        self.llm = llm

    async def generate(self, request: IllustrationRequest) -> List[IllustrationResult]:
        """本文からシーンを抽出し、各シーンの挿絵を生成して返す。"""
        text = request.scene_text or ""
        if self.llm is not None:
            scenes = await self.extractor.extract_scenes_with_llm(text, self.llm, max_scenes=3)
        else:
            scenes = self.extractor.extract_scenes(text, max_scenes=3)

        results: List[IllustrationResult] = []
        for scene in scenes:
            results.append(await self.illustrator.generate_for_scene(scene, request))
        return results
