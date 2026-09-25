import pytest
from src.config.commercial_beat_sheet import COMMERCIAL_40EP_BEATS


def test_beat_sheet_covers_all_episodes():
    """40話ビートシートが1話から40話まで抜け漏れなくカバーしていることを検証"""
    covered = set()
    for beat in COMMERCIAL_40EP_BEATS:
        start, end = beat["range"]
        # 範囲内のすべての話数をカバー集合に追加
        for ep in range(start, end + 1):
            covered.add(ep)
    
    # 1話から40話までがすべてカバーされているか
    expected = set(range(1, 41))
    assert covered == expected, f"カバー不足または重複: 不足={expected - covered}, 重複={covered - expected}"


def test_beat_sheet_phases_are_defined():
    """各ビートにフェーズが定義されていることを検証"""
    for beat in COMMERCIAL_40EP_BEATS:
        assert "phase" in beat
        assert isinstance(beat["phase"], str)
        assert len(beat["phase"].strip()) > 0


def test_beat_sheet_directives_are_defined():
    """各ビートにディレクティブが定義されていることを検証"""
    for beat in COMMERCIAL_40EP_BEATS:
        assert "directive" in beat
        assert isinstance(beat["directive"], str)
        assert len(beat["directive"].strip()) > 0