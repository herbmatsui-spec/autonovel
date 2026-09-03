"""挿絵（シーン）抽出・生成サービス。

本文から重要なシーンを抽出し、Imagen で挿絵を生成する。
シーン抽出は LLM を使う方式と、LLM がなくても動くヒューリスティック方式の
両方を用意し、低性能環境でも段階的に導入できる。
"""

import logging
import re
import time

from src.models.illustration import IllustrationRequest, IllustrationResult, IllustrationType
from src.services.illustration.model_selector import resolve_request_model
from src.services.illustration.prompts import (
    apply_safety_modifier,
    apply_yonkoma_safety_modifier,
    build_scene_prompt,
    build_yonkoma_prompt,
)
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

    def extract_scenes(self, text: str, max_scenes: int = 3) -> list[str]:
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

    async def extract_scenes_with_llm(self, text: str, llm, max_scenes: int = 3) -> list[str]:
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

    def __init__(self, image_service: ImageService, llm: object | None = None):
        self.extractor = SceneExtractor()
        self.illustrator = SceneIllustrator(image_service)
        self.llm = llm

    async def generate(self, request: IllustrationRequest) -> list[IllustrationResult]:
        """本文からシーンを抽出し、各シーンの挿絵を生成して返す。"""
        text = request.scene_text or ""
        if self.llm is not None:
            scenes = await self.extractor.extract_scenes_with_llm(text, self.llm, max_scenes=3)
        else:
            scenes = self.extractor.extract_scenes(text, max_scenes=3)

        results: list[IllustrationResult] = []
        for scene in scenes:
            results.append(await self.illustrator.generate_for_scene(scene, request))
        return results


class YonkomaPlanner:
    """1話分の本文を 6 コマ分の短いシーン要約に分割する。

    LLM がある場合は「起承転結 + 余韻2」を意識した JSON を返させ、
    ない場合は段落ベース + キーワード重みで ``panels`` 個に分割する。
    """

    _PROMPT_TEMPLATE = (
        "以下の小説本文を、起承転結 + 余韻2 の合計 {panels} コマに分割し、"
        "各コマを 1〜2 文の日本語要約で表してください。\n"
        '出力は JSON 配列のみ (例: ["...", "...", ...])。\n\n'
        "{text}"
    )

    async def plan_with_llm(self, text: str, llm, panels: int = 6) -> list[str]:
        """LLM を使って ``panels`` 個の要約を生成する。失敗時は ``plan_heuristic`` にフォールバック。"""
        panels = max(3, min(int(panels or 6), 6))
        prompt = self._PROMPT_TEMPLATE.format(panels=panels, text=text[:2400])
        try:
            resp = await llm.generate_json(
                model_name=getattr(llm, "default_model", "gemini-2.0-flash"),
                prompt=prompt,
                system_instruction=(
                    "You are a comic storyboard planner. "
                    f"Return exactly {panels} short Japanese summaries as a JSON array."
                ),
            )
            data = resp.metadata if hasattr(resp, "metadata") else resp
            if isinstance(data, dict):
                data = data.get("panels", data.get("scenes", data.get("result", [])))
            if isinstance(data, list):
                cleaned = [str(s).strip() for s in data if str(s).strip()]
                if cleaned:
                    return self._normalize(cleaned, panels)
        except Exception as e:  # noqa: BLE001
            logger.warning("Yonkoma LLM planning failed, fallback to heuristic: %s", e)
        return self.plan_heuristic(text, panels=panels)

    def plan_heuristic(self, text: str, panels: int = 6) -> list[str]:
        """LLM が無い/失敗時に ``panels`` 個の要約を作る。"""
        panels = max(3, min(int(panels or 6), 6))
        paragraphs = [p.strip() for p in re.split(r"\n{2,}|[。！？]\s*", text) if p.strip()]
        # 短すぎる段落は除外 (抽出不能を避けるため最低 8 文字)
        paragraphs = [p for p in paragraphs if len(p) >= 8]
        if not paragraphs:
            return ["(導入)"] * panels

        # 6 分割マッピング: 段落数と panels が一致しない場合は等間隔で割当
        if len(paragraphs) >= panels:
            step = len(paragraphs) / panels
            chosen: list[str] = []
            for i in range(panels):
                idx = int(i * step)
                idx = min(idx, len(paragraphs) - 1)
                chosen.append(paragraphs[idx])
            return chosen

        # 段落数が panels 未満: 先頭から使い、不足分は末尾を再要約
        padded = list(paragraphs)
        while len(padded) < panels:
            padded.append(paragraphs[-1] if paragraphs else "(継続)")
        return padded[:panels]

    @staticmethod
    def _normalize(items: list[str], panels: int) -> list[str]:
        """LLM 出力を ``panels`` 個に整える。"""
        if len(items) >= panels:
            return items[:panels]
        # 不足分は末尾の要素で埋める (欠落防止)
        last = items[-1] if items else "(継続)"
        return items + [last] * (panels - len(items))


class YonkomaIllustrator:
    """6 コマ分のシーン要約から 1 枚のストーリー画像プロンプトを組み立てて Imagen を呼ぶ。"""

    def __init__(self, image_service: ImageService):
        self.image_service = image_service

    async def generate(
        self,
        episode_text: str,
        request: IllustrationRequest,
        panels: int = 6,
        summaries: list[str] | None = None,
    ) -> IllustrationResult:
        start = time.time()
        book_context = request.book_context or {}
        if summaries is None:
            summaries = YonkomaPlanner().plan_heuristic(episode_text, panels=panels)

        prompt = build_yonkoma_prompt(summaries, book_context, panels=panels)
        prompt = apply_yonkoma_safety_modifier(prompt, request.safety_level)

        image_url = await self.image_service.generate(
            prompt=prompt,
            model=resolve_request_model(request),
            aspect_ratio=request.aspect_ratio or "3:4",
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
