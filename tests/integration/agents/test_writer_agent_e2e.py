"""E2E tests for WriterAgent with hierarchical memory."""
from src.agents.writer_agent import WriterAgent
from src.stores.vector_store import InMemoryVectorStore


def test_writer_agent_e2e(tmp_path):
    store = InMemoryVectorStore()
    save_dir = tmp_path / "memory_e2e"

    # 1. 第1話執筆
    agent1 = WriterAgent(vector_store=store, save_directory=save_dir)
    tool_calls_ep1 = [
        {
            "name": "update_emotion",
            "arguments": {"source": "Alice", "target": "Bob", "emotion": "trust", "delta": 0.8, "reason": "命を救われた"},
        },
        {
            "name": "set_active_hook",
            "arguments": {"hook": "Bobの正体を暴く"},
        },
    ]
    agent1.write_episode(1, "二人の出会いと救出", simulated_tool_calls=tool_calls_ep1)
    assert agent1.memory_manager.core_memory.character_emotions["Alice->Bob"]["trust"] == 0.8

    # 2. 第2話執筆時: プロンプトに第1話の CoreMemory 感情が反映されること
    system_prompt = agent1.build_system_prompt(2)
    assert "Alice->Bob" in system_prompt
    assert "trust" in system_prompt
    assert "0.8" in system_prompt

    # 3. Agent 再起動 (別インスタンスで save_dir から復元)
    agent2 = WriterAgent(vector_store=store, save_directory=save_dir)
    agent2.memory_manager.load_state(save_dir)
    assert agent2.memory_manager.core_memory.character_emotions["Alice->Bob"]["trust"] == 0.8
    assert "Bobの正体を暴く" in agent2.memory_manager.core_memory.active_hooks
