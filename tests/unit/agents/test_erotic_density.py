import pytest
from src.agents.erotic.density_controller import EroticDensityController

def test_density_target_adjustment():
    controller = EroticDensityController(base_density=0.3)
    target = controller.get_target_density(current_chapter=5, reader_drop_risk=0.8)
    # 離脱リスクが高い場合、密度を引き上げる
    assert target >= 0.3
