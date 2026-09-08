"""Unit tests for FourLayerCompressor end-to-end pipeline and ProtectedContext pinning (Part 5 / Steps 55-60)."""

import pytest

from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import (
    CompressionConfig,
    CompressedContextResult,
    ProtectedContext,
)


def test_four_layer_compressor_pipeline_basic():
    """Test full 4-layer compression pipeline execution without protected context (Step 58)."""
    compressor = FourLayerCompressor(
        config=CompressionConfig(max_tokens=300, target_reduction_ratio=0.5, cache_enabled=False)
    )

    raw_text = """
    第10話：王都の動乱
    アリスは王宮の大広間でバルフィア帝国の使節団と対峙していた。
    使節団の代表であるクローデル卿は、不可侵条約の破棄と領地割譲を要求した。
    背後ではボブが密かに抜刀の構えをとり、緊迫した空気が漂う。
    一方、地下牢では暗殺者が脱出計画を進めていた。
    """

    entities = [
        {"name": "アリス", "labels": ["Character"], "properties": {"role": "筆頭魔術師"}},
        {"name": "ボブ", "labels": ["Character"], "properties": {"role": "護衛剣士"}},
        {"name": "バルフィア帝国", "labels": ["Country"], "properties": {"role": "敵対国"}},
        {"name": "不可侵条約", "labels": ["Rule"], "properties": {"role": "外交協定"}},
    ]
    relations = [
        {"source": "アリス", "target": "ボブ", "type": "信頼関係"},
        {"source": "バルフィア帝国", "target": "アリス", "type": "敵対脅迫"},
    ]

    result = compressor.compress(
        raw_text=raw_text,
        entities=entities,
        relations=relations,
        scene_type="political",
        bypass_cache=True,
    )

    assert isinstance(result, CompressedContextResult)
    assert result.final_token_count > 0
    assert result.final_token_count <= 300
    assert len(result.final_context_text) > 0
    assert result.layer1 is not None
    assert result.layer2 is not None
    assert result.layer3 is not None
    assert result.layer4 is not None


def test_four_layer_compressor_with_protected_context_pinning():
    """Test guaranteed retention of active characters and foreshadowing IDs (Steps 55-57)."""
    compressor = FourLayerCompressor(
        config=CompressionConfig(max_tokens=150, cache_enabled=False)
    )

    raw_text = """
    決戦の夜。アリスとキャロルは暗黒竜の巣窟に足を踏み入れた。
    遠くの街では商人が宴を開き、吟遊詩人が昔の英雄譚を歌っている。
    壁にはFS-999の古代文字が刻まれていた。
    """

    entities = [
        {"name": "アリス", "labels": ["Character"], "properties": {"role": "現在同席の主人公"}},
        {"name": "キャロル", "labels": ["Character"], "properties": {"role": "現在同席の仲間"}},
        {"name": "吟遊詩人", "labels": ["Character"], "properties": {"role": "遠くのモブ"}},
        {"name": "FS-999", "labels": ["Lore"], "properties": {"role": "滅びの予言伏線"}},
    ]
    relations = [
        {"source": "アリス", "target": "キャロル", "type": "共闘"},
        {"source": "アリス", "target": "FS-999", "type": "因縁解明"},
    ]

    protected = ProtectedContext(
        active_characters=["アリス", "キャロル"],
        pending_foreshadowing_ids=["FS-999"],
    )

    # Compress under very tight token budget (150 tokens)
    result = compressor.compress(
        raw_text=raw_text,
        entities=entities,
        relations=relations,
        scene_type="combat",
        max_tokens=120,
        protected_context=protected,
        bypass_cache=True,
    )

    # Pinned items must never be dropped even under severe budget limits
    assert "アリス" in result.layer4.retained_entities
    assert "キャロル" in result.layer4.retained_entities
    assert "FS-999" in result.layer4.retained_entities

    # Metrics check
    assert result.layer4.pinned_count >= 2
    assert result.layer4.retention_rate > 0.0
    assert "【現在同席】" in result.final_context_text
