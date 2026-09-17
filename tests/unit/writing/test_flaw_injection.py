"""
Unit tests for Character Flaw Injection in ContextBuilderAgent.
PLAN 03 - Step 7: 毒要素注入単体テスト
"""
from __future__ import annotations

from src.agents.context_builder_agent import resolve_character_flaw
from src.models.character_flaw import CharacterFlawProfile


def test_resolve_character_flaw_defaults_to_preset():
    """Flawが未設定のキャラクター情報から自動的にプリセットのFlawプロファイルが生成されること"""
    char_data = {
        "name": "アルト",
        "personality": "熱血・お人好し",
        "ability": "付与魔法",
    }
    profile = resolve_character_flaw(char_data)
    assert isinstance(profile, CharacterFlawProfile)
    assert profile.character_name == "アルト"
    assert profile.surface_persona != ""
    assert profile.secret_flaw.motive_type != ""
    assert profile.secret_flaw.inner_monologue_sample != ""
    assert profile.secret_flaw.physical_trigger != ""


def test_resolve_character_flaw_preserves_custom_flaw():
    """明示的に設定されたFlawが存在する場合、それが優先して保持されること"""
    custom_flaw = {
        "motive_type": "絶対的支配欲",
        "inner_monologue_sample": "全員を平伏させてやる",
        "physical_trigger": "右手の指先を鳴らす",
    }
    char_data = {
        "name": "レオン",
        "personality": "冷静沈着",
        "secret_flaw": custom_flaw,
        "target_of_contempt": "旧ギルドマスター",
    }
    profile = resolve_character_flaw(char_data)
    assert profile.character_name == "レオン"
    assert profile.secret_flaw.motive_type == "絶対的支配欲"
    assert profile.target_of_contempt == "旧ギルドマスター"
