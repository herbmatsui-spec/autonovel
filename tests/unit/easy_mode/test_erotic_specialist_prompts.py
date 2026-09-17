from __future__ import annotations

from config.erotic_pacing import EroticCurve
from src.engine.prompts.erotic_specialist import EroticSpecialist


def test_erotic_specialist_get_config_value():
    specialist = EroticSpecialist()
    preset = {"custom_key": "custom_val"}
    assert specialist._get_erotic_config_value(preset, "custom_key", "default") == "custom_val"
    assert specialist._get_erotic_config_value(preset, "missing_key", "default") == "default"
    assert specialist._get_erotic_config_value({}, "any_key", "fallback") == "fallback"


def test_erotic_specialist_metaphor_filter():
    specialist = EroticSpecialist()
    raw = "静かな夜の部屋で、ふたりの視線が交差する。"
    processed = specialist.metaphor_filter(raw, intensity=1)
    assert isinstance(processed, str)
    assert len(processed) > 0


def test_erotic_specialist_build_scene_prompt():
    specialist = EroticSpecialist()
    curve = EroticCurve.create_default(intensity=2)

    context = {
        "platform_preset": "kakuyomu_romance",
        "character_info": "主人公とヒロイン",
        "scene_setting": "月明かりの部屋",
    }
    prompt = specialist.build_scene_prompt(curve, context)
    assert isinstance(prompt, str)
    assert len(prompt) > 50
