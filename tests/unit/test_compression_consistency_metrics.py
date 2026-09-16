import pytest
from src.services.compression import FourLayerCompressor, ProtectedContext, SceneFlowHistory

def test_compression_pipeline_outputs_high_consistency_metrics():
    compressor = FourLayerCompressor()
    text = "勇者アレンは聖剣バルムンクを構えた。背後には魔法使いエレナが控えている。古の予言『月が紅く染まる時』の謎が迫る。"
    protected = ProtectedContext(
        active_characters=["アレン", "エレナ"],
        pending_foreshadowing_ids=["月が紅く染まる時"],
    )
    result = compressor.compress(text, protected_context=protected)
    
    assert result.metrics is not None
    assert result.metrics.character_retention_score == 1.0
    assert result.metrics.foreshadowing_retention_score == 1.0
    assert result.metrics.overall_consistency_score >= 0.80