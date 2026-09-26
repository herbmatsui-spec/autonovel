"""Unit tests for VoiceProfile."""
from src.agents.memory.voice_profile import VoiceProfile


def test_profile_influences_dialogue():
    profile = VoiceProfile(
        character_name="Alice",
        speech_patterns=["〜かしら", "皮肉めいた言い回し"],
        vocabulary_level="advanced",
        emotional_leakage=0.1,
    )

    instr = profile.render_instruction()
    assert "Alice" in instr
    assert "皮肉めいた言い回し" in instr
    assert "内心をほとんど表情に出さない" in instr

    # シリアライズ確認
    d = profile.to_dict()
    restored = VoiceProfile.from_dict(d)
    assert restored.character_name == "Alice"
    assert restored.emotional_leakage == 0.1
