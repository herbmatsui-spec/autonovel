"""Unit tests for build_fused_emotional_context_prompt."""
from src.fusion.config import FusionConfig
from src.fusion.engine import FusionEngine
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.pipeline.prompt_builder import build_fused_emotional_context_prompt
from src.stores.vector_store import InMemoryVectorStore


def test_fused_prompt_includes_conflicts():
    store = InMemoryVectorStore()
    config = FusionConfig()

    # ep14 のデータを作成（episode_id=15 の執筆時に参照される）
    v_anno = EmotionalVector(episode_id="ep14")
    v_anno.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep14"))
    store.upsert("annotation", "ep14:A->B", v_anno)

    v_pipe = EmotionalVector(episode_id="ep14")
    v_pipe.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.6, 0.5, "...", "ep14"))
    store.upsert("pipeline", "ep14:A->B", v_pipe)

    engine = FusionEngine(store, config)

    prompt = build_fused_emotional_context_prompt(episode_id=15, fusion_engine=engine)
    assert "[直前話からの引き継ぎ感情（融合済み）]" in prompt
    assert "⚠ 矛盾検出（要確認）" in prompt
    assert "A→B" in prompt
    assert "annotation" in prompt
    assert "pipeline" in prompt
