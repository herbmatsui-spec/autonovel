import pytest
from src.backend.tension_curve_config import EMOTIONAL_CURVES

def test_zamaa_curve_exists():
    """Step 2: ざまぁ曲線 zamaa_heavy が定義されているか確認"""
    assert "zamaa_heavy" in EMOTIONAL_CURVES, "EMOTIONAL_CURVES should contain 'zamaa_heavy'"
    
    curve = EMOTIONAL_CURVES["zamaa_heavy"]
    assert isinstance(curve, list), "zamaa_heavy curve should be a list"
    assert len(curve) > 0, "zamaa_heavy curve should not be empty"
    assert all(isinstance(p, tuple) and len(p) == 2 for p in curve), "Each point in curve should be a tuple of (progress, value)"
