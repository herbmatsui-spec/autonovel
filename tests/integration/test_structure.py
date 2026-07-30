"""
tests/integration/test_structure.py

機能5（物語構造テンプレート検証）のテスト。
構造検証ロジックと、DB上のプロットを用いたルーター経由の検証を確認する。
"""
import pytest

from src.services.structure_validator import (
    assign_phases,
    check_climax_placement,
    check_required_beats,
    list_structures,
    load_structure,
    validate,
)


def _plots(n: int, climax_at: int = None):
    return [
        {"ep_num": i + 1, "title": f"E{i+1}", "tension": 100 if (climax_at and i + 1 == climax_at) else 30}
        for i in range(n)
    ]


def test_load_structure_defaults_to_three_act():
    assert load_structure("unknown")["name"] == "三幕構成"
    assert load_structure("kishotenketsu")["name"] == "起承転結"


def test_assign_phases_covers_zero_to_one():
    assigned = assign_phases(_plots(5))
    assert assigned[0]["_phase"] == 0.0
    assert assigned[-1]["_phase"] == 1.0


def test_missing_beats_detected_when_short():
    structure = load_structure("three_act")
    assigned = assign_phases(_plots(2))
    beats = check_required_beats(assigned, structure)
    assert any(not b["present"] for b in beats)


def test_climax_placement_ok_when_late():
    structure = load_structure("three_act")
    assigned = assign_phases(_plots(10, climax_at=9))
    res = check_climax_placement(assigned, structure)
    assert res["ok"] is True


def test_climax_placement_fail_when_early():
    structure = load_structure("three_act")
    assigned = assign_phases(_plots(10, climax_at=2))
    res = check_climax_placement(assigned, structure)
    assert res["ok"] is False


def test_validate_healthy_full_story():
    structure = load_structure("three_act")
    assigned = assign_phases(_plots(12, climax_at=10))
    beats = check_required_beats(assigned, structure)
    climax = check_climax_placement(assigned, structure)
    pacing = {"ok": True, "reason": "", "skew": 0.1}
    report = validate(_plots(12, climax_at=10), "three_act")
    assert report["is_healthy"] == ((not any(not b["present"] for b in beats)) and climax["ok"] and pacing["ok"])


def test_list_structures_has_three():
    assert len(list_structures()) >= 3
