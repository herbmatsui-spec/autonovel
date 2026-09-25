"""Arbitrator logic for resolving conflicts and fusing emotional vectors."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Set, Tuple
from collections import defaultdict

from src.fusion.config import FusionConfig, load_fusion_config
from src.fusion.conflict_detector import ConflictDetector
from src.fusion.models import Conflict, FusedValue, FusedVector, SourceVector
from src.pipeline.emotional_residue import EmotionType


class ConflictResolutionStoreProtocol(Protocol):
    """手動解決ストアのプロトコル"""
    def get_resolution(self, conflict_id: str) -> Optional[Dict[str, Any]]: ...


class Arbitrator:
    """複数ソースの感情ベクトルを仲裁・融合して単一の FusedVector を生成する"""

    def __init__(
        self,
        config: Optional[FusionConfig] = None,
        conflict_detector: Optional[ConflictDetector] = None,
        resolution_store: Optional[Any] = None,
    ):
        self.config = config or load_fusion_config()
        self.conflict_detector = conflict_detector or ConflictDetector(self.config)
        self.resolution_store = resolution_store

    def fuse(self, source_vectors: List[SourceVector]) -> FusedVector:
        """複数の SourceVector を融合する。
        
        Args:
            source_vectors: 収集された SourceVector リスト
            
        Returns:
            融合後の FusedVector
        """
        if not source_vectors:
            return FusedVector()

        # 1. 矛盾検出
        conflicts = self.conflict_detector.detect(source_vectors)
        conflict_map: Dict[Tuple[Tuple[str, str], EmotionType], Conflict] = {
            (c.pair, c.emotion): c for c in conflicts
        }

        # 2. 全ソースの (pair, emotion) データをグループ化
        # key: ((src, tgt), emo) -> list of (namespace, value, confidence)
        items: Dict[Tuple[Tuple[str, str], EmotionType], List[Tuple[str, float, float]]] = defaultdict(list)
        for sv in source_vectors:
            ns = sv.namespace
            conf = sv.confidence
            for (src, tgt, emo), val in sv.vector.signals.items():
                items[((src, tgt), emo)].append((ns, float(val), conf))

        fused_values: Dict[Tuple[str, str, EmotionType], FusedValue] = {}

        for (pair, emo), entries in items.items():
            src_char, tgt_char = pair
            # 信頼度降順でソート
            sorted_entries = sorted(entries, key=lambda x: x[2], reverse=True)
            top_entry = sorted_entries[0]
            top_ns, top_val, top_conf = top_entry

            is_conflicted = (pair, emo) in conflict_map
            conflict_obj = conflict_map.get((pair, emo))

            # Step 13: 解決済みストアが存在し、解決レコードがある場合のオーバーライド
            resolved = None
            if is_conflicted and conflict_obj and self.resolution_store:
                try:
                    resolved = self.resolution_store.get_resolution(conflict_obj.conflict_id)
                except Exception:
                    resolved = None

            if resolved:
                # 手動解決適用: resolution = annotation | rule_engine | pipeline | manual
                res_type = resolved.get("resolution")
                manual_val = resolved.get("manual_value")
                if res_type == "manual" and manual_val is not None:
                    final_val = float(manual_val)
                    primary_src = "manual"
                else:
                    match_entry = next((e for e in sorted_entries if e[0] == res_type), top_entry)
                    final_val = match_entry[1]
                    primary_src = match_entry[0]

                fused_values[(src_char, tgt_char, emo)] = FusedValue(
                    value=final_val,
                    primary_source=primary_src,
                    contributing_sources=[e[0] for e in sorted_entries],
                    confidence=1.0,  # 解決済みは確実な信頼度 1.0 扱い
                )
            elif not is_conflicted:
                # 矛盾なし: 最高信頼度のソースをそのまま採用
                fused_values[(src_char, tgt_char, emo)] = FusedValue(
                    value=top_val,
                    primary_source=top_ns,
                    contributing_sources=[e[0] for e in sorted_entries],
                    confidence=top_conf,
                )
            else:
                # 矛盾あり
                mode = self.config.mode
                contributing = [e[0] for e in sorted_entries]

                if mode == "highest_confidence":
                    final_val = top_val
                    primary_src = top_ns
                else:
                    # weighted_blend: blend_weights と confidence を掛け合わせて加重平均
                    total_weight = 0.0
                    weighted_sum = 0.0
                    for ns, val, conf in sorted_entries:
                        w = self.config.blend_weights.get(ns, 0.1) * conf
                        total_weight += w
                        weighted_sum += val * w

                    if total_weight > 0:
                        final_val = round(weighted_sum / total_weight, 4)
                    else:
                        final_val = top_val
                    primary_src = top_ns

                # 矛盾時ペナルティ適用
                penalized_conf = round(max(0.0, min(1.0, top_conf * (1.0 - self.config.conflict_penalty))), 4)
                fused_values[(src_char, tgt_char, emo)] = FusedValue(
                    value=round(final_val, 4),
                    primary_source=primary_src,
                    contributing_sources=contributing,
                    confidence=penalized_conf,
                )

        return FusedVector(
            values=fused_values,
            conflicts=conflicts,
            metadata={"mode": self.config.mode},
        )
