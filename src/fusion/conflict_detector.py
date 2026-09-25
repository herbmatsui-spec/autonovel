"""Conflict detector between multiple emotional vector sources."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from src.fusion.config import FusionConfig, load_fusion_config
from src.fusion.models import Conflict, SourceVector
from src.pipeline.emotional_residue import EmotionType


class ConflictDetector:
    """異なる感情ソース間の矛盾を検出するクラス"""

    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or load_fusion_config()

    def detect(self, source_vectors: List[SourceVector]) -> List[Conflict]:
        """与えられた複数の SourceVector から矛盾を検出する。
        
        Args:
            source_vectors: 収集された SourceVector リスト
            
        Returns:
            検出された Conflict のリスト
        """
        if len(source_vectors) < 2:
            return []

        # 1. (pair, emotion) ごとに (source_namespace, value, confidence) をグループ化
        grouped: Dict[Tuple[Tuple[str, str], EmotionType], List[Tuple[str, float, float]]] = defaultdict(list)

        for sv in source_vectors:
            ns = sv.namespace
            conf = sv.confidence
            vec = sv.vector

            # vec内の全シグナル走査: key is (src, tgt, EmotionType)
            for (src, tgt, emo), val in vec.signals.items():
                pair = (src, tgt)
                grouped[(pair, emo)].append((ns, float(val), conf))

        conflicts: List[Conflict] = []
        sig_thresh = self.config.significance_threshold
        conf_thresh = self.config.conflict_threshold

        # 2. 各 (pair, emotion) について矛盾判定
        for (pair, emo), entries in grouped.items():
            if len(entries) < 2:
                continue

            # 信頼度降順ソート
            sorted_entries = sorted(entries, key=lambda x: x[2], reverse=True)
            top1 = sorted_entries[0]
            top2 = sorted_entries[1]

            v1, c1 = top1[1], top1[2]
            v2, c2 = top2[1], top2[2]

            # 符号反転判定: (v1 > 0 and v2 < 0) or (v1 < 0 and v2 > 0)
            sign_flip = (v1 > 0 and v2 < 0) or (v1 < 0 and v2 > 0)
            both_significant = abs(v1) >= sig_thresh and abs(v2) >= sig_thresh
            diff_large = abs(v1 - v2) >= conf_thresh

            if sign_flip and both_significant and diff_large:
                conflict = Conflict(
                    pair=pair,
                    emotion=emo,
                    sources=sorted_entries,
                )
                conflicts.append(conflict)

        return conflicts
