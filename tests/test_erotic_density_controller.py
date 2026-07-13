"""
tests/test_erotic_density_controller.py
密度コントローラのユニットテスト。
"""
from src.services.erotic_density_controller import EroticDensityController


def test_should_allow_peak_edge_cases():
    controller = EroticDensityController()
    assert controller.should_allow_peak([]) is True
    assert controller.should_allow_peak([3]) is True
    assert controller.should_allow_peak([4, 5, 4]) is False

def test_recommend_intensity_by_progress():
    controller = EroticDensityController()
    # 蠎冗乢 (10%)
    assert controller.recommend_intensity(1, 10, 5) <= 2
    # 荳ｭ逶､ (50%)
    assert controller.recommend_intensity(5, 10, 3) == 3
    # 邨ら乢 (90%)
    assert controller.recommend_intensity(9, 10, 4) >= 4

def test_recommend_intensity_bounds():
    controller = EroticDensityController()
    # 華企剞5
    assert controller.recommend_intensity(9, 10, 6) <= 5
    # 華矩剞1
    assert controller.recommend_intensity(1, 10, 0) >= 1

def test_avg_intensity_empty():
    controller = EroticDensityController()
    assert controller.compute_avg_intensity([]) == 0.0

def test_avg_intensity_normal():
    controller = EroticDensityController()
    assert controller.compute_avg_intensity([1, 2, 3, 4, 5]) == 3.0

def test_suggest_next_intensity():
    controller = EroticDensityController()
    # 騾｣邯壹ヴ繝ｼ繧ｯ縺後↑縺・・縺ｧ縺昴・縺ｾ縺ｾ
    assert controller.suggest_next_intensity([1, 2, 3], 4) == 4
    # 騾｣邯壹ヴ繝ｼ繧ｯ4,4 縺後≠繧九・縺ｧ1谿ｵ髫惹ｸ九￡繧・
    assert controller.suggest_next_intensity([1, 2, 4, 4], 4) == 3
    # 逶ｴ霑代′4莉･荳翫↑縺ｮ縺ｧ1谿ｵ髫惹ｸ九￡繧・
    assert controller.suggest_next_intensity([1, 2, 3, 5], 4) == 3
    # 譛菴主､縺ｯ1
    assert controller.suggest_next_intensity([1, 2, 4, 4], 1) == 1
