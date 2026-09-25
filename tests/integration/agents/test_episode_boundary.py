"""Integration tests for episode boundary auto compact and save."""
from src.agents.writer_agent import WriterAgent
from src.stores.vector_store import InMemoryVectorStore


def test_auto_compact_and_save(tmp_path):
    store = InMemoryVectorStore()
    save_dir = tmp_path / "mem_boundary"
    agent = WriterAgent(vector_store=store, save_directory=save_dir)

    # 1話執筆
    agent.write_episode(1, "旅立ち")

    # ArchivalMemory にエピソード要約が挿入されているか確認
    summaries = agent.memory_manager.archival_memory.search("感情ハイライト", k=5)
    assert len(summaries) >= 1
    assert "第1話" in summaries[0].content

    # ディスクに CoreMemory が保存されているか確認
    assert (save_dir / "core_memory.json").exists()
