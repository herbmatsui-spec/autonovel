"""Integration tests for WriterAgent using fused emotional context prompt."""
from src.agents.writer_agent import WriterAgent
from src.fusion.config import FusionConfig
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import InMemoryVectorStore


def test_writer_uses_fused_prompt():
    store = InMemoryVectorStore()
    config = FusionConfig()

    # ep14 のデータを投入
    v_anno = EmotionalVector(episode_id="ep14")
    v_anno.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep14"))
    store.upsert("annotation", "ep14:A->B", v_anno)

    agent = WriterAgent(vector_store=store, config=config, fusion_enabled=True)

    # 第15話用のプロンプト
    prompt = agent.get_emotional_prompt(episode=15)
    assert "[直前話からの引き継ぎ感情（融合済み）]" in prompt
    assert "高信頼度（作者指定・プロット整合）" in prompt
    assert "A→B: 恐怖(0.8)" in prompt
    assert "[annotation]" in prompt

    system_prompt = agent.build_system_prompt(episode=15, base_prompt="あなたはプロ作家です。")
    assert "あなたはプロ作家です。" in system_prompt
    assert "高信頼度（作者指定・プロット整合）" in system_prompt
