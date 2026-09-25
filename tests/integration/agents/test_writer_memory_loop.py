"""Integration tests for WriterAgent write loop and memory update."""
from src.agents.writer_agent import WriterAgent
from src.stores.vector_store import InMemoryVectorStore


def test_write_episode_updates_core_memory(tmp_path):
    store = InMemoryVectorStore()
    save_dir = tmp_path / "memory_agent"
    agent = WriterAgent(vector_store=store, save_directory=save_dir)

    # 執筆中にツール呼び出し（AがBに恐怖+0.6）が発生したケースをシミュレート
    tool_calls = [
        {
            "name": "update_emotion",
            "arguments": {
                "source": "A",
                "target": "B",
                "emotion": "fear",
                "delta": 0.6,
                "reason": "裏切りの露見",
            },
        }
    ]

    manuscript = agent.write_episode(
        episode=1,
        plot_outline="第1話: 陰謀の始まり",
        simulated_tool_calls=tool_calls,
    )

    assert "第1話" in manuscript
    # CoreMemory に更新が反映されていること
    assert agent.memory_manager.core_memory.character_emotions["A->B"]["fear"] == 0.6
    assert agent.memory_manager.core_memory.character_emotions["A->B"]["cause"] == "裏切りの露見"

    # ディスクに保存されていること
    core_file = save_dir / "core_memory.json"
    assert core_file.exists()
