"""Comprehensive regression tests for Week 5 Hierarchical Agent Memory."""
from src.agent.memory.branch_manager import BranchMemoryManager
from src.agent.memory.cached_archival import CachedArchivalMemory
from src.agent.memory.compaction import CompactionPolicy
from src.agent.memory.core_memory import CoreMemory
from src.agent.memory.interfaces import MemoryEntry
from src.agent.memory.voice_profile import VoiceProfile
from src.agents.writer_agent import WriterAgent
from src.fusion.models import FusedValue, FusedVector
from src.pipeline.emotional_residue import EmotionType
from src.stores.vector_store import InMemoryVectorStore


def test_core_memory_persists_across_restarts(tmp_path):
    store = InMemoryVectorStore()
    save_dir = tmp_path / "persist_mem"

    # セッション1
    agent1 = WriterAgent(vector_store=store, save_directory=save_dir)
    agent1.memory_manager.update_emotion("Hero", "Villain", "fear", 0.7, reason="敗北")
    agent1.memory_manager.save_state(save_dir)

    # セッション2 (再起動)
    agent2 = WriterAgent(vector_store=store, save_directory=save_dir)
    loaded = agent2.memory_manager.load_state(save_dir)
    assert loaded is True
    assert agent2.memory_manager.core_memory.character_emotions["Hero->Villain"]["fear"] == 0.7


def test_tool_calls_update_core_memory(tmp_path):
    store = InMemoryVectorStore()
    agent = WriterAgent(vector_store=store, save_directory=tmp_path)

    agent.tool_handler.handle_call("update_emotion", {
        "source": "A", "target": "B", "emotion": "affection", "delta": 0.4, "reason": "告白"
    })
    assert agent.memory_manager.core_memory.character_emotions["A->B"]["affection"] == 0.4


def test_archival_search_works():
    store = InMemoryVectorStore()
    cached_archival = CachedArchivalMemory(vector_store=store)
    cached_archival.insert(MemoryEntry("s1", "第3話での激しい決闘と別れ"))

    results = cached_archival.search("決闘")
    assert len(results) >= 1
    assert results[0].id == "s1"


def test_compaction_moves_old_data():
    core = CoreMemory()
    store = InMemoryVectorStore()
    archival = CachedArchivalMemory(vector_store=store)
    policy = CompactionPolicy(max_tokens=10, stale_episode_threshold=3)

    core.update_emotion("A", "B", "fear", 0.5, episode_label="ep1")
    core.update_emotion("C", "D", "trust", 0.9, episode_label="ep6")

    res = policy.compact(core, current_episode=6, archival_memory=archival)
    assert res["compacted"] is True
    assert "A->B" not in core.character_emotions
    assert "C->D" in core.character_emotions


def test_fused_vector_injected():
    fv = FusedVector()
    fv.values[("Alpha", "Beta", EmotionType.TRUST)] = FusedValue(0.85, "annotation")

    core = CoreMemory()
    core.load_fused_vector(fv, episode_label="ep10")
    assert core.character_emotions["Alpha->Beta"]["trust"] == 0.85
    assert core.character_emotions["Alpha->Beta"]["primary_source"] == "annotation"


def test_branch_isolation(tmp_path):
    bm = BranchMemoryManager(project_id="test_iso", base_dir=tmp_path)
    main_mem = CoreMemory()
    main_mem.update_emotion("A", "B", "affection", 0.5)
    bm.save_branch("main", main_mem)

    if_mem = bm.fork_branch("main", "if_route")
    if_mem.update_emotion("A", "B", "affection", -0.7)
    bm.save_branch("if_route", if_mem)

    re_main = bm.load_branch("main")
    re_if = bm.load_branch("if_route")
    assert re_main.character_emotions["A->B"]["affection"] == 0.5
    assert re_if.character_emotions["A->B"]["affection"] == -0.2


def test_voice_profile_affects_dialogue():
    vp = VoiceProfile("Bob", speech_patterns=["〜でござる"], vocabulary_level="archaic", emotional_leakage=0.8)
    rendered = vp.render_instruction()
    assert "Bob" in rendered
    assert "〜でござる" in rendered
    assert "感情が言動に素直に表れる" in rendered
