from src.agents.erotic_integrity import (
    COMBAT_KEYWORDS,
    SCENE_TYPES,
    EroticCurve,
    EroticPoint,
    SceneTypeDetector,
)


def test_erotic_integrity_facade_constants():
    """ファサード経由で定数が正常にアクセスできることの検証。"""
    assert "erotic" in SCENE_TYPES
    assert "combat" in SCENE_TYPES
    assert len(COMBAT_KEYWORDS) > 0


def test_erotic_integrity_facade_classes():
    """ファサード経由で各クラスが正しくインスタンス化できることの検証。"""
    point = EroticPoint(position=0.5, intensity=75.0)
    assert point.position == 0.5
    assert point.intensity == 75.0

    curve = EroticCurve(points=[point])
    assert len(curve.points) == 1

    detector = SceneTypeDetector()
    assert detector is not None
