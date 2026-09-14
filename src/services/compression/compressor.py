"""Four-Layer Context Compressor (Step 31)."""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any
from sqlalchemy.orm import Session

from src.services.compression.models import (
    CompressionConfig,
    CompressedContextResult,
    SceneType,
    ProtectedContext,
)
from src.services.compression.layer1_keywords import Layer1KeywordExtractor
from src.services.compression.layer2_subgraph import Layer2SubgraphExtractor
from src.services.compression.layer3_abstraction import Layer3ConceptAbstractor
from src.services.compression.layer4_trimming import Layer4SceneTrimmer
from src.services.compression.cache import CompressionCache

logger = logging.getLogger(__name__)


class FourLayerCompressor:
    """Integrated 4-layer context compression engine with caching."""

    def __init__(
        self,
        config: CompressionConfig | None = None,
        age_client: Any = None,
        redis_client: Any = None,
    ) -> None:
        self.config = config or CompressionConfig()
        self.age_client = age_client

        # 各層の初期化
        self.layer1 = Layer1KeywordExtractor(
            top_n=self.config.top_keywords,
            min_score=0.01,
            tokenizer_config=self.config.sudachi,
        )
        self.layer2 = Layer2SubgraphExtractor(
            max_hops=self.config.max_hops,
            relevance_threshold=self.config.relevance_threshold,
            age_client=self.age_client,
        )
        self.layer3 = Layer3ConceptAbstractor()
        self.layer4 = Layer4SceneTrimmer(
            max_tokens=self.config.max_tokens,
            preserve_categories=self.config.preserve_categories,
        )
        self.cache = CompressionCache(
            redis_client=redis_client,
            default_ttl=self.config.cache_ttl_seconds,
        )

    def compress(
        self,
        raw_text: str,
        *,
        entities: list[dict[str, Any]] | None = None,
        relations: list[dict[str, Any]] | None = None,
        session: Session | None = None,
        graph_name: str | None = None,
        book_id: int | None = None,
        ep_num: int | None = None,
        scene_type: SceneType | None = None,
        max_tokens: int | None = None,
        bypass_cache: bool = False,
        scene_weights: dict[SceneType, float] | None = None,
        protected_context: ProtectedContext | None = None,
    ) -> CompressedContextResult:
        """Execute the full 4-layer compression pipeline with protected context pinning."""
        start_time = time.perf_counter()
        target_scene = scene_type or self.config.scene_type
        budget = max_tokens or self.config.max_tokens

        if not raw_text or not raw_text.strip():
            empty_trim = self.layer4.trim(
                self.layer3.abstract(self.layer2.extract_from_memory([], [], [])),
                scene_type=target_scene,
                max_tokens=budget,
                scene_weights=scene_weights,
                protected_context=protected_context,
            )
            return CompressedContextResult(
                layer4=empty_trim,
                final_context_text="",
                final_token_count=0,
                overall_reduction_ratio=0.0,
                elapsed_ms=0.0,
            )

        # キャッシュ確認
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
        cache_key = self.cache.make_key(book_id, ep_num, target_scene, content_hash)

        if self.config.cache_enabled and not bypass_cache:
            cached = self.cache.get(cache_key)
            if cached:
                try:
                    result = CompressedContextResult.model_validate(cached)
                    result.from_cache = True
                    result.elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return result
                except Exception as e:
                    logger.debug(f"Cache validation error: {e}")

        # Layer 1: キーフレーズ抽出
        layer1_out = self.layer1.extract(raw_text)

        # Layer 2: 2-hopサブグラフ抽出 & 枝刈り (ProtectedContextをシードに確実に含める)
        seeds = list(layer1_out.extracted_keywords)
        if protected_context:
            for c in protected_context.active_characters:
                if c and c not in seeds:
                    seeds.append(c)
            for f in protected_context.pending_foreshadowing_ids:
                if f and f not in seeds:
                    seeds.append(f)
            for p in protected_context.pinned_entities:
                if p and p not in seeds:
                    seeds.append(p)

        if session and graph_name and self.age_client:
            layer2_out = self.layer2.extract_from_age(
                session=session,
                graph_name=graph_name,
                seed_names=seeds,
                keyword_scores=layer1_out.keyword_scores,
            )
        else:
            layer2_out = self.layer2.extract_from_memory(
                entities=entities or [],
                relations=relations or [],
                seed_names=seeds,
                keyword_scores=layer1_out.keyword_scores,
            )

        # Layer 3: 概念レベル抽象化・カテゴリ化
        layer3_out = self.layer3.abstract(
            subgraph=layer2_out,
            raw_text=raw_text,
        )

        # Layer 4: シーン適応型動的トリミング (Step 58)
        layer4_out = self.layer4.trim(
            abstraction_output=layer3_out,
            scene_type=target_scene,
            max_tokens=budget,
            keywords=seeds,
            original_token_count=layer1_out.original_token_count,
            scene_weights=scene_weights,
            protected_context=protected_context,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        final_text = layer4_out.compressed_text
        final_tokens = layer4_out.token_count

        reduction = 0.0
        if layer1_out.original_token_count > 0:
            reduction = max(0.0, 1.0 - (final_tokens / layer1_out.original_token_count))

        result = CompressedContextResult(
            layer1=layer1_out,
            layer2=layer2_out,
            layer3=layer3_out,
            layer4=layer4_out,
            final_context_text=final_text,
            final_token_count=final_tokens,
            overall_reduction_ratio=round(reduction, 3),
            from_cache=False,
            elapsed_ms=round(elapsed_ms, 2),
        )

        # キャッシュ保存
        if self.config.cache_enabled:
            try:
                self.cache.set(cache_key, result.model_dump())
            except Exception as e:
                logger.debug(f"Failed to cache compression result: {e}")

        return result


__all__ = ["FourLayerCompressor"]
