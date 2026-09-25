"""Unit tests for hook generator."""
from src.agent.hooks.hook_generator import generate_hooks
from src.agent.memory.core_memory import CoreMemory


def test_generate_hooks_from_fear():
    core = CoreMemory()
    core.update_emotion("A", "B", "fear", 0.85, reason="裏切りの恐怖")

    hooks = generate_hooks(core)
    assert len(hooks) == 1
    assert "AのBに対する恐怖(0.85)" in hooks[0]
    assert "裏切りの恐怖" in hooks[0]


def test_generate_hooks_with_active_hooks():
    core = CoreMemory()
    core.active_hooks.append("秘密の暴露")
    core.update_emotion("A", "B", "anger", 0.7)

    hooks = generate_hooks(core)
    assert "秘密の暴露" in hooks
    assert any("怒り(0.7)" in h for h in hooks)
