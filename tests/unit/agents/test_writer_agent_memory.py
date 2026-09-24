"""Unit tests for WriterAgent memory initialization and attributes."""
from src.agents.writer_agent import WriterAgent
from src.stores.vector_store import InMemoryVectorStore


def test_agent_has_memory_manager():
    store = InMemoryVectorStore()
    agent = WriterAgent(vector_store=store)

    assert agent.memory_manager is not None
    assert agent.tool_handler is not None
    assert agent.tools is not None
    assert len(agent.tools) == 7

    # システムプロンプトにメモリ操作指示が含まれていること
    system_prompt = agent.build_system_prompt(episode=1)
    assert "update_emotion" in system_prompt
    assert "recall_similar_scene" in system_prompt
