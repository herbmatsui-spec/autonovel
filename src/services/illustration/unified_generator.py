"""統合イラスト生成エンジン（全IllustrationTypeを単一モデルで扱う）。

設計原則:
- P1: モデルIDは `config/image_models.py` のみに書く。
- P2: 種別差は `strategies/` に閉じる（本体に IllustrationType の if を持たない）。
- P3: 後処理は任意依存。Pillow が無い環境でも生成自体は成功する。

処理順: prompt 生成 → API 生成 → 保存 → 品質ゲート → 超解像 → 写植。
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from config.image_models import IMAGE_MODEL_CATALOG, get_image_model_spec
from src.models.illustration import (
    IllustrationRequest,
    IllustrationResult,
)
from src.services.illustration.character_ref import CharacterReferenceManager
from src.services.illustration.clients import (
    ImageClientProtocol,
    PermanentClientError,
    TransientClientError,
    build_client,
)
from src.services.illustration.config import UnifiedIllustrationConfig
from src.services.illustration.quality_gate import QualityGate
from src.services.illustration.strategies import get_strategy, is_multi_panel
from src.services.illustration.typesetter import Typesetter
from src.services.illustration.upscaler import Upscaler

logger = logging.getLogger(__name__)

# 複数コマ種別は写植が効く（単発絵は写植しない）
TYPESETTABLE_TYPES = ("yonkoma", "manga_24panel")


class UnifiedIllustrationGenerator:
    """表紙 / 挿絵 / 立ち絵 / 6コマ / 24コマ的统一生成器。"""

    def __init__(
        self,
        config: Optional[UnifiedIllustrationConfig] = None,
        client: Optional[ImageClientProtocol] = None,
        llm: Any = None,
        image_service: Any = None,
    ) -> None:
        self.config = config or UnifiedIllustrationConfig()
        self.llm = llm
        self._injected_client = client
        self._image_service = image_service
        self._client: Optional[ImageClientProtocol] = None
        #: Legacy 経路が「旧 ImageService フォールバック」由来かどうか
        self._legacy_from_fallback = bool(image_service) or bool(
            self.config.use_legacy_client
        )
        self._strategies: Dict[Any, Any] = {}

        self.quality_gate = QualityGate()
        self.upscaler = Upscaler(
            scale_factor=self.config.upscale_factor,
            target_width=self.config.target_upscale_width,
        )
        self.typesetter = Typesetter(
            grid_cols=self.config.typeset_grid_cols,
            grid_rows=self.config.typeset_grid_rows,
            font_size=self.config.font_size,
        )
        self.character_refs = CharacterReferenceManager(self.config.character_ref_dir)

    # ---- クライアント ----

    @property
    def client(self) -> ImageClientProtocol:
        """実効クライアント。注入されたものは最優先。"""
        if self._client is None:
            if self._injected_client is not None:
                self._client = self._injected_client
            else:
                # ロールバック指定 / 旧 ImageService 注入時は Legacy 経路を使う
                legacy = self.config.use_legacy_client or self._image_service is not None
                spec = get_image_model_spec(
                    "imagen_fast" if legacy else self.config.model_key
                )
                self._client = build_client(
                    spec.key,
                    api_key=self.config.api_key,
                    mock_mode=self.config.mock_mode,
                    image_service=self._image_service if legacy else None,
                )
        return self._client

    @property
    def model_used(self) -> str:
        """実効モデルID（UI・永続化へ渡す）。"""
        client = self.client
        return getattr(client, "model_id", self.config.model_id)

    def estimate_cost(self, request: IllustrationRequest) -> float:
        """1件の概算コスト（USD）。Legacy 経路は tier 解決結果に従う。"""
        client = self.client
        if getattr(client, "name", "") == "legacy_imagen":
            spec = self._legacy_spec(request)
            if spec is not None:
                return spec.cost_per_image_usd
        return get_image_model_spec(self.config.model_key).cost_per_image_usd

    def _legacy_spec(self, request: IllustrationRequest) -> Any | None:
        """Legacy 経路の tier 解決結果をカタログ仕様として返す。"""
        try:
            from src.services.illustration.model_selector import resolve_request_model

            legacy_id = resolve_request_model(request)
            for spec in IMAGE_MODEL_CATALOG.values():
                if spec.model_id == legacy_id:
                    return spec
        except Exception as exc:  # noqa: BLE001
            logger.debug("Legacy cost lookup skipped: %s", exc)
        return None

    def get_strategy(self, request: IllustrationRequest) -> Any:
        """種別に対応するプロンプト戦略（キャッシュ付き）。"""
        key = getattr(request.illustration_type, "value", request.illustration_type)
        if key not in self._strategies:
            self._strategies[key] = get_strategy(
                request.illustration_type, self.config, llm=self.llm
            )
        return self._strategies[key]

    # ---- 生成 ----

    async def generate(self, request: IllustrationRequest) -> IllustrationResult:
        """1 件を生成する。品質ゲート NG でも例外は投げない。"""
        start = time.perf_counter()
        strategy = self.get_strategy(request)

        prompt = await self._build_prompt(strategy, request)
        negative_prompt = strategy.build_negative_prompt(request)
        aspect_ratio = request.aspect_ratio or self.config.aspect_ratio_for(
            request.illustration_type
        )
        references = self._resolve_references(request)

        try:
            self._apply_legacy_tier(request)
            image = await self._generate_with_retry(
                prompt=prompt,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                reference_images=references,
            )
        except (PermanentClientError, TransientClientError) as exc:
            logger.error("Image generation failed permanently: %s", exc)
            raise

        image_path = self._save_image(image.data, request)
        type_value = str(getattr(request.illustration_type, "value", request.illustration_type))

        # --- 品質ゲート（記録のみ。NGでも生成は成功扱い） ---
        quality_payload: Optional[Dict[str, Any]] = None
        quality_passed = True
        if self.config.enable_quality_gate:
            multi_panel = is_multi_panel(request.illustration_type)
            evaluation = self.quality_gate.evaluate(
                image_path,
                thresholds=self.config.thresholds_for(
                    request.illustration_type, multi_panel=multi_panel
                ),
            )
            quality_passed = evaluation.is_valid
            quality_payload = evaluation.to_dict()
            if not quality_passed:
                logger.info(
                    "Quality gate flagged %s (still returning result): %s",
                    image_path,
                    evaluation.reasons,
                )

        # --- 超解像（任意） ---
        upscaled_path: Optional[Path] = None
        final_path = image_path
        if self.config.enable_upscale:
            upscaled_path = self.upscaler.upscale(image_path)
            final_path = upscaled_path

        # --- 写植（任意・複数コマのみ） ---
        typeset_applied = False
        dialogues = (request.book_context or {}).get("dialogues")
        if self.config.enable_typesetting and dialogues and type_value in TYPESETTABLE_TYPES:
            final_path = self.typesetter.apply(final_path, dialogues)
            typeset_applied = True

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        result = IllustrationResult(
            request=request,
            # Legacy 経路は既にファイル保存済みなので meta 経由で URL を受け取る
            image_url=str(getattr(image, "meta", {}).get("url", "") or ""),
            prompt=prompt,
            model_used=self.model_used,
            generation_time_ms=elapsed_ms,
            image_path=image_path,
            quality=quality_payload,
            upscaled_path=upscaled_path,
            final_path=final_path if final_path != image_path else None,
            typeset_applied=typeset_applied,
            estimated_cost_usd=self.estimate_cost(request),
        )
        # image_url が空ならローカルパスから静的URLを補う（UI 互換）
        if not result.image_url:
            result.image_url = result.resolved_url()
        return result

    async def generate_batch(
        self,
        requests: Sequence[IllustrationRequest],
    ) -> List[Optional[IllustrationResult]]:
        """複数を並列生成する。1件失敗しても全体は止めない（failed は None）。"""
        if not requests:
            return []
        results = await asyncio.gather(
            *(self.generate(request) for request in requests),
            return_exceptions=True,
        )
        out: List[Optional[IllustrationResult]] = []
        for request, result in zip(requests, results):
            if isinstance(result, BaseException):
                logger.error(
                    "Illustration generation failed (%s): %s",
                    getattr(request.illustration_type, "value", "?"),
                    result,
                )
                out.append(None)
            else:
                out.append(result)
        return out

    # ---- 内部処理 ----

    def _apply_legacy_tier(self, request: IllustrationRequest) -> None:
        """旧 ImageService フォールバック時のみ、リクエストの tier を反映する。

        - フォールバック（`image_service` 注入 / `use_legacy_client`）:
          旧 `resolve_request_model` と同じ規則（cover/character→ultra、
          episode→fast、R15→quality）で従来挙動を維持する。
        - 明示的に Imagen tier を選んでいる場合: カタログの指定を尊重する
          （ユーザーの選択をリクエストの AUTO が上書きしない）。
        """
        client = self.client
        if getattr(client, "name", "") != "legacy_imagen":
            return
        if not self._legacy_from_fallback:
            return
        try:
            from src.services.illustration.model_selector import resolve_request_model

            client.model_id = resolve_request_model(request)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Legacy tier resolution skipped: %s", exc)

    async def _build_prompt(self, strategy: Any, request: IllustrationRequest) -> str:
        """戦略の同期/非同期プロンプト生成をどちらでも扱えるようにする。"""
        async_builder = getattr(strategy, "build_prompt_async", None)
        if callable(async_builder):
            return await async_builder(request)
        return strategy.build_prompt(request)

    def _resolve_references(self, request: IllustrationRequest) -> List[Path]:
        """キャラクター参照画像を集める（無効・不在なら空）。"""
        if not self.config.enable_character_reference:
            return []
        characters = (request.book_context or {}).get("characters") or []
        if isinstance(characters, str):
            characters = [characters]
        if not characters:
            return []
        return self.character_refs.get_references(request.book_id, list(characters))

    async def _generate_with_retry(
        self,
        prompt: str,
        negative_prompt: str,
        aspect_ratio: str,
        reference_images: Sequence[Path],
    ) -> Any:
        """一時エラーは指数バックオフでリトライする。"""
        attempts = max(0, int(self.config.max_retries)) + 1
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                return await self.client.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    aspect_ratio=aspect_ratio,
                    reference_images=tuple(reference_images),
                )
            except TransientClientError as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break
                delay = self.config.retry_backoff_sec * (2**attempt)
                logger.warning(
                    "Transient image error (attempt %d/%d): %s; retrying in %.2fs",
                    attempt + 1,
                    attempts,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
        raise last_error or TransientClientError("Image generation failed.")

    def _save_image(self, data: bytes, request: IllustrationRequest) -> Path:
        """生成画像を `{output_root}/{book_id}/` 配下へ保存する。"""
        if not data:
            # 何も得られなかった場合は 1x1 の透明 PNG を置いて後段を成立させる
            data = _EMPTY_PNG
        book_dir = self.config.output_root / str(request.book_id)
        book_dir.mkdir(parents=True, exist_ok=True)

        type_value = str(getattr(request.illustration_type, "value", request.illustration_type))
        episode = request.episode_number or 0
        filename = f"{type_value}_ep{episode}_{int(time.time() * 1000)}.png"
        path = book_dir / filename
        # 同名衝突に備えて連番を足す（冪等性担保）
        counter = 1
        while path.exists():
            path = book_dir / f"{type_value}_ep{episode}_{int(time.time() * 1000)}_{counter}.png"
            counter += 1
        path.write_bytes(data)
        return path

    # ---- 試算 ----

    def estimate_cost_batch(self, requests: Sequence[IllustrationRequest]) -> float:
        """複数件の概算コスト合計（USD）。"""
        return round(sum(self.estimate_cost(r) for r in requests), 6)

    def estimate_time(self, request: IllustrationRequest) -> float:
        """1件の概算所要秒数（同期処理の目安）。"""
        if is_multi_panel(request.illustration_type):
            return 15.0
        return 10.0


# 1x1 透明 PNG（データが空だった場合のフォールバック）
_EMPTY_PNG = bytes(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


__all__ = ["TYPESETTABLE_TYPES", "UnifiedIllustrationGenerator"]
