"""Fusion engine for aggregating, arbitrating and caching emotional vectors across pairs."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.fusion.arbitrator import Arbitrator
from src.fusion.collector import VectorCollector
from src.fusion.config import FusionConfig, load_fusion_config
from src.fusion.models import Conflict, FusedValue, FusedVector
from src.pipeline.emotional_residue import EmotionalSignal, EmotionalVector, EmotionType
from src.stores.conflict_store import ConflictStore
from src.stores.vector_store import VectorStore


class FusionEngine:
    """全ペアの一括感情融合およびキャッシュ永続化を担うメインエンジン"""

    def __init__(
        self,
        vector_store: VectorStore,
        config: Optional[FusionConfig] = None,
        arbitrator: Optional[Arbitrator] = None,
        collector: Optional[VectorCollector] = None,
        conflict_store: Optional[ConflictStore] = None,
    ):
        self.vector_store = vector_store
        self.config = config or load_fusion_config()
        self.conflict_store = conflict_store or ConflictStore()
        self.arbitrator = arbitrator or Arbitrator(self.config, resolution_store=self.conflict_store)
        self.collector = collector or VectorCollector(self.vector_store, self.config)

    def _discover_all_pairs(self, namespaces: List[str]) -> Set[Tuple[str, str]]:
        """各ネームスペース内のキーやデータから、登場する全キャラクターペアを検出する"""
        pairs: Set[Tuple[str, str]] = set()

        for ns in namespaces:
            keys = self.vector_store.get_namespace_keys(ns)
            for k in keys:
                # パターン1: "ep01:A->B" or "A->B"
                match = re.search(r'([A-Za-z0-9_\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]+)->([A-Za-z0-9_\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]+)', k)
                if match:
                    pairs.add((match.group(1), match.group(2)))

            # 保存されている全ベクトルの signals からもペアを検出
            try:
                vectors = self.vector_store.get_all(ns)
                for v in vectors:
                    for (src, tgt, emo) in v.signals.keys():
                        pairs.add((src, tgt))
            except Exception:
                pass

        return pairs

    def fuse_all(self, episode: int) -> FusedVector:
        """指定エピソードに関する全キャラクターペアの感情ベクトルを一括融合する"""
        namespaces = self.collector.namespaces
        pairs = self._discover_all_pairs(namespaces)

        all_values: Dict[Tuple[str, str, EmotionType], FusedValue] = {}
        all_conflicts: List[Conflict] = []

        for pair in pairs:
            # 各ペアのソースベクトルを収集
            sources = self.collector.collect_all(pair, episode=episode)
            if not sources:
                continue

            # 仲裁・融合実行
            fused_pair = self.arbitrator.fuse(sources)
            all_values.update(fused_pair.values)
            all_conflicts.extend(fused_pair.conflicts)

        fused = FusedVector(
            values=all_values,
            conflicts=all_conflicts,
            metadata={"episode": episode, "pairs_count": len(pairs)},
        )

        return fused

    def persist_fused(self, fused: FusedVector, episode: int) -> None:
        """融合結果を 'fused' ネームスペースにキャッシュ保存し、矛盾ストアに記録する"""
        # 1. 矛盾レコードを保存
        if fused.conflicts:
            self.conflict_store.record_conflicts(fused.conflicts, episode=episode)

        # 2. 全体 FusedVector を保存（JSON文字列化して保存）
        fused_vec_wrapper = EmotionalVector(episode_id=f"ep{episode}")
        fused_vec_wrapper.metadata["fused_payload"] = fused.to_dict()

        # ペアごとのシグナルにも変換して VectorStore に保存
        pairs_dict: Dict[Tuple[str, str], EmotionalVector] = {}
        for (src, tgt, emo), f_val in fused.values.items():
            pair = (src, tgt)
            if pair not in pairs_dict:
                pairs_dict[pair] = EmotionalVector(episode_id=f"ep{episode}")
            
            sig = EmotionalSignal(
                source=src,
                target=tgt,
                emotion_type=emo,
                value=f_val.value,
                confidence=f_val.confidence,
                evidence_span=f"fused:primary={f_val.primary_source}",
                episode_id=f"ep{episode}",
                cause=f"fused from {','.join(f_val.contributing_sources)}",
            )
            pairs_dict[pair].set_signal(sig)
            fused_vec_wrapper.set_signal(sig)

        # 全体キー保存
        self.vector_store.upsert("fused", f"ep{episode}", fused_vec_wrapper)

        # 各ペアキー保存
        for (src, tgt), pair_vec in pairs_dict.items():
            pair_vec.metadata["fused_payload"] = fused.to_dict()
            self.vector_store.upsert("fused", f"ep{episode}:{src}->{tgt}", pair_vec)

    def get_fused(self, episode: int) -> Optional[FusedVector]:
        """キャッシュされた FusedVector を取得する"""
        vec = self.vector_store.get_latest("fused", ("*", "*"))
        if not vec:
            all_vecs = self.vector_store.get_all("fused")
            for v in all_vecs:
                if v.episode_id == f"ep{episode}":
                    vec = v
                    break

        if vec and "fused_payload" in vec.metadata:
            return FusedVector.from_dict(vec.metadata["fused_payload"])
        return None

    def fuse_and_persist(self, episode: int) -> FusedVector:
        """融合を実行し、同時に永続化するコンビニエンスメソッド"""
        fused = self.fuse_all(episode)
        self.persist_fused(fused, episode)
        return fused
