"""
QualityMetrics / QualityMetricsCollector の単体テスト
"""

from src.backend.workflows.quality_metrics import QualityMetrics, QualityMetricsCollector


def _make(ep_num: int, genre: str = "fantasy", integrity: bool = True, causal: bool = True, rate: float = 0.9, dogfeed_ok: bool = True) -> QualityMetrics:
    return QualityMetrics(
        ep_num=ep_num,
        integrity_ok=integrity,
        causal_ok=causal,
        rate=rate,
        ac_iter=1,
        threshold=70,
        timestamp=1.0,
        genre=genre,
        dogfeed_ok=dogfeed_ok,
        causal_reason="",
    )


def test_overall_quality_perfect():
    m = _make(1, rate=1.0)
    assert abs(m.overall_quality - 1.0) < 1e-9


def test_overall_quality_low_when_failed():
    m = _make(2, integrity=False, causal=False, rate=0.0, dogfeed_ok=False)
    assert m.overall_quality == 0.0


def test_overall_quality_partial():
    m = _make(3, integrity=True, causal=False, rate=0.5)
    # 0.4 + 0.0 + 0.2 + 0.05 = 0.65
    assert abs(m.overall_quality - 0.65) < 1e-9


def test_collector_record_and_get():
    c = QualityMetricsCollector()
    m = _make(3)
    c.record(m)
    assert c.get(3) is m
    assert c.get(999) is None


def test_collector_genre_baseline():
    c = QualityMetricsCollector()
    c.record(_make(1, "fantasy"))
    c.record(_make(2, "fantasy", causal=False))
    trend = c.get_quality_trend("fantasy")
    assert trend["count"] == 2
    assert trend["integrity_rate"] == 1.0
    assert trend["causal_rate"] == 0.5


def test_collector_overall_trend():
    c = QualityMetricsCollector()
    c.record(_make(1, "a"))
    c.record(_make(2, "b", integrity=False))
    trend = c.get_quality_trend()
    assert trend["count"] == 2
    assert abs(trend["integrity_rate"] - 0.5) < 1e-9
