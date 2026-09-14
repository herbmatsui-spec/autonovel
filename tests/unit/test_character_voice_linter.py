import pytest
from src.services.character.voice_linter import VoiceLinter
from src.services.character.voice_normalizer import VoiceNormalizer
from src.models.character_voice_profile import CharacterVoiceProfile

def test_voice_linter_and_normalizer():
    profile = CharacterVoiceProfile(
        character_name="Test",
        first_person=["俺"],
        second_person=["お前"],
        endings=["だぜ"],
        forbidden_words=["禁句"],
        catchphrases=[],
        sample_dialogue=""
    )
    linter = VoiceLinter()
    normalizer = VoiceNormalizer()

    # 一人称違反、語尾違反のあるセリフ
    dialogue = "私は嬉しいです。"
    
    # リンターで違反検知
    errors = linter.check(dialogue, profile)
    assert len(errors) > 0
    
    # ノーマライザーで修正
    fixed = normalizer.normalize(dialogue, profile)
    
    # 修正後の検証（簡易的な修正ができているか確認）
    assert "俺" in fixed
    assert "だぜ" in fixed
