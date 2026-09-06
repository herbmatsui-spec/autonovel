"""Compressor wrapper for benchmark execution."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from src.services.compression import FourLayerCompressor, CompressionConfig
from src.services.compression.models import SceneType


class CompressorWrapper:
    """Wrapper to run compression pipeline for benchmarks."""

    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self.compressor = FourLayerCompressor(config=self.config)

    def compress_episode(
        self,
        text: str,
        scene_type: SceneType = "general",
        entities: Optional[List[Dict[str, Any]]] = None,
        relations: Optional[List[Dict[str, Any]]] = None,
        book_id: int = 1,
        ep_num: int = 1,
        bypass_cache: bool = True,
    ) -> Dict[str, Any]:
        """Compress a single episode and return metrics dict."""
        result = self.compressor.compress(
            text,
            entities=entities or [],
            relations=relations or [],
            book_id=book_id,
            ep_num=ep_num,
            scene_type=scene_type,
            bypass_cache=bypass_cache,
        )

        return {
            "final_text": result.final_context_text,
            "final_tokens": result.final_token_count,
            "original_tokens": result.layer1.original_token_count if result.layer1 else 0,
            "reduction_ratio": result.overall_reduction_ratio,
            "elapsed_ms": result.elapsed_ms,
            "from_cache": result.from_cache,
            "scene_type": result.layer4.scene_type if result.layer4 else scene_type,
            "retained_entities": result.layer4.retained_entities if result.layer4 else [],
            "layer1_keywords": result.layer1.extracted_keywords if result.layer1 else [],
            "layer2_nodes": len(result.layer2.nodes) if result.layer2 else 0,
            "layer2_edges": len(result.layer2.edges) if result.layer2 else 0,
            "layer3_concepts": result.layer3.abstract_concepts if result.layer3 else [],
            "layer3_categories": list(result.layer3.categorized_facts.keys()) if result.layer3 else [],
        }

    def compress_episodes(
        self,
        episodes: List[Dict[str, Any]],
        book_id: int = 1,
    ) -> List[Dict[str, Any]]:
        """Compress multiple episodes sequentially."""
        results = []
        for i, ep in enumerate(episodes, 1):
            ep_result = self.compress_episode(
                text=ep["text"],
                scene_type=ep.get("scene_type", "general"),
                entities=ep.get("entities"),
                relations=ep.get("relations"),
                book_id=book_id,
                ep_num=ep.get("ep_num", i),
            )
            ep_result["ep_num"] = ep.get("ep_num", i)
            ep_result["scene_type"] = ep.get("scene_type", "general")
            results.append(ep_result)
        return results


def run_compression(
    text: str,
    scene_type: SceneType = "general",
    entities: Optional[List[Dict[str, Any]]] = None,
    relations: Optional[List[Dict[str, Any]]] = None,
    book_id: int = 1,
    ep_num: int = 1,
    max_tokens: int = 1500,
) -> Dict[str, Any]:
    """Convenience function for single compression run."""
    config = CompressionConfig(max_tokens=max_tokens, cache_enabled=False)
    wrapper = CompressorWrapper(config)
    return wrapper.compress_episode(
        text=text,
        scene_type=scene_type,
        entities=entities,
        relations=relations,
        book_id=book_id,
        ep_num=ep_num,
        bypass_cache=True,
    )


__all__ = ["CompressorWrapper", "run_compression"]