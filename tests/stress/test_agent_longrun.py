"""Stress and long-run test simulating 50 episodes of continuous writing."""
from src.agents.writer_agent import WriterAgent
from src.stores.vector_store import InMemoryVectorStore


def test_agent_longrun_50_episodes(tmp_path):
    store = InMemoryVectorStore()
    save_dir = tmp_path / "longrun_mem"
    agent = WriterAgent(vector_store=store, save_directory=save_dir)

    # 50エピソード連続執筆
    for ep in range(1, 51):
        tool_calls = [
            {
                "name": "update_emotion",
                "arguments": {
                    "source": f"Char_{ep % 5}",
                    "target": f"Char_{(ep + 1) % 5}",
                    "emotion": "tension",
                    "delta": 0.1,
                    "reason": f"Episode {ep} battle event",
                },
            }
        ]
        manuscript = agent.write_episode(
            episode=ep,
            plot_outline=f"エピソード{ep}の戦闘と展開",
            simulated_tool_calls=tool_calls,
        )
        assert f"第{ep}話" in manuscript

    # 50話完了後の検証
    tokens = agent.memory_manager.core_memory.estimate_tokens()
    # 圧縮ポリシーによりトークン数が暴走せず安定していること
    assert tokens < 3000

    # ArchivalMemory に50件の要約が蓄積されていること
    archived_entries = agent.memory_manager.archival_memory._entries
    assert len(archived_entries) >= 50
