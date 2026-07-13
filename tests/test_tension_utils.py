import pytest

from src.backend.tension_curve_config import EMOTIONAL_CURVES, select_curve_by_hook
from src.backend.tension_utils import calculate_progress, get_target_tension, select_tension_curve


def test_select_tension_curve():
    # Story type priority
    assert select_tension_curve("romance", "zamaa") == "zamaa_heavy"
    # Genre mapping
    assert select_tension_curve("revenge") == "zamaa_heavy"
    assert select_tension_curve("mystery") == "slow_burn"
    # Default
    assert select_tension_curve("unknown") == "standard"

def test_calculate_progress():
    assert calculate_progress(1, 10) == 0.0
    assert calculate_progress(5, 10) == 0.4
    assert calculate_progress(10, 10) == 0.9
    assert calculate_progress(1, 0) == 0.0

def test_get_target_tension_boundaries():
    # Test start boundary
    assert get_target_tension("standard", -0.1) == EMOTIONAL_CURVES["standard"][0][1]
    # Test end boundary
    assert get_target_tension("standard", 1.1) == EMOTIONAL_CURVES["standard"][-1][1]

def test_get_target_tension_interpolation():
    # standard: (0.0, 0.2) -> (0.2, 0.4)
    # Midpoint 0.1 should be 0.3
    tension = get_target_tension("standard", 0.1)
    assert tension == pytest.approx(0.3)

    # zamaa_heavy: (0.1, 0.8) -> (0.4, 0.9)
    # progress 0.25 is 1/3 of the way between 0.1 and 0.4
    # 0.8 + (0.9 - 0.8) * (0.25 - 0.1) / (0.4 - 0.1) = 0.8 + 0.1 * 0.15 / 0.3 = 0.8 + 0.05 = 0.85
    tension_zamaa = get_target_tension("zamaa_heavy", 0.25)
    assert tension_zamaa == pytest.approx(0.85)

def test_get_target_tension_invalid_curve():
    # Should fallback to default curve
    tension = get_target_tension("non_existent", 0.0)
    assert tension == EMOTIONAL_CURVES["standard"][0][1]

def test_select_curve_by_hook_known():
    assert select_curve_by_hook("catharsis") == "zamaa_heavy"
    assert select_curve_by_hook("empathy_peak") == "slow_burn"
    assert select_curve_by_hook("serenity") == "slow_burn"

def test_select_curve_by_hook_unknown():
    assert select_curve_by_hook("unknown_hook") == "standard"
    assert select_curve_by_hook("") == "standard"

def test_get_target_tension_with_hook_name():
    # catharsis -> zamaa_heavy: (0.0, 0.3) -> (0.1, 0.8)
    # progress 0.1 は (0.0, 0.3) -> (0.1, 0.8) の区間内で endpoint なので 0.8
    tension = get_target_tension("standard", 0.1, hook_name="catharsis")
    assert tension == pytest.approx(0.8)

def test_get_target_tension_hook_name_none_preserves_legacy():
    # curve_name が優先される
    tension = get_target_tension("standard", 0.1, hook_name=None)
    assert tension == pytest.approx(0.3)

def test_get_target_tension_unknown_hook_falls_back():
    tension = get_target_tension("standard", 0.1, hook_name="unknown_hook")
    assert tension == pytest.approx(0.3)
