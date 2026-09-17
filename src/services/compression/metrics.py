"""Quantitative consistency and retention metrics for context compression."""
from __future__ import annotations
import re
from src.services.compression.models import (
    CompressionQualityMetrics,
    ProtectedContext,
    TrimmedContextOutput,
)

def calculate_consistency_metrics(
    raw_text: str,
    trimmed_output: TrimmedContextOutput,
    protected_context: ProtectedContext | None = None,
    original_keywords: list[str] | None = None,
) -> CompressionQualityMetrics:
    """圧縮後テキストの情報保持率と整合性スコアを定量計算"""
    compressed = trimmed_output.compressed_text

    # 1. キャラクター保持率 (Protected active_characters)
    char_score = 1.0
    if protected_context and protected_context.active_characters:
        target_chars = [c for c in protected_context.active_characters if c in raw_text]
        if target_chars:
            hit = sum(1 for c in target_chars if c in compressed)
            char_score = hit / len(target_chars)

    # 2. 未回収伏線保持率 (Protected pending_foreshadowing_ids)
    foreshadow_score = 1.0
    if protected_context and protected_context.pending_foreshadowing_ids:
        target_fs = [f for f in protected_context.pending_foreshadowing_ids if f in raw_text]
        if target_fs:
            hit = sum(1 for f in target_fs if f in compressed)
            foreshadow_score = hit / len(target_fs)

    # 3. 固有名詞保持率 (カタカナ語および漢字複合語)
    proper_nouns = set(re.findall(r"[ァ-ンヴー]{3,}|[一-龯]{4,}", raw_text))
    noun_score = 1.0
    if proper_nouns:
        hit = sum(1 for n in proper_nouns if n in compressed)
        noun_score = hit / len(proper_nouns)

    # 4. セマンティック密度（トークンあたりの採用事実数）
    facts_count = len(trimmed_output.retained_entities)
    density_score = min(1.0, (facts_count * 10) / max(1, trimmed_output.token_count))

    # 5. 総合加重平均
    overall = (char_score * 0.35) + (foreshadow_score * 0.35) + (noun_score * 0.20) + (density_score * 0.10)

    return CompressionQualityMetrics(
        character_retention_score=round(char_score, 3),
        foreshadowing_retention_score=round(foreshadow_score, 3),
        proper_noun_retention_score=round(noun_score, 3),
        semantic_density_score=round(density_score, 3),
        overall_consistency_score=round(overall, 3),
    )
