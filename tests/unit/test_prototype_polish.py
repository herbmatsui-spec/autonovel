"""
tests/unit/test_prototype_polish.py - ステップ 9: polish_adapter の単体テスト
"""

import pytest
from src.backend.workflows.narrative_state import NarrativeState
from src.prototype.polish_adapter import polish


def test_polish_normal_text():
    """通常テキストの校正テスト（重複句読点の除去など）"""
    raw_text = "光の石が輝いた、、そして静寂が訪れた。。"
    result = polish(raw_text)
    assert "、、" not in result
    assert "。。" not in result
    assert "光の石が輝いた、そして静寂が訪れた。" in result


def test_polish_with_continuity_violations():
    """NarrativeState ハブに連続性違反が存在する場合の修正指摘付与テスト"""
    hub = NarrativeState()
    hub.continuity_violations.append({"field": "hp", "msg": "回復薬なしでHPが急増しています"})

    raw_text = "凛は立ち上がった。"
    result = polish(raw_text, hub=hub)

    assert "以下の矛盾を修正:" in result
    assert "回復薬なしでHPが急増しています" in result
    assert "凛は立ち上がった。" in result
