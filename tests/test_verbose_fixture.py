import pytest
from tests.fixtures.llm_verbose_fixture import verbose_fixture
from src.models.sharp_edge import SharpEdgeSpec

def test_verbose_fixture_load():
    """フィクスチャが正しくロードされ、データが存在することを検証する"""
    assert verbose_fixture.samples is not None
    assert len(verbose_fixture.samples) > 0
    assert "ending_pullback" in verbose_fixture.samples

def test_verbose_fixture_get_random_description():
    """ランダムな記述が正しく取得できることを検証する"""
    edge_type = "ending_pullback"
    desc = verbose_fixture.get_random_description(edge_type)
    assert isinstance(desc, str)
    assert len(desc) > 0
    assert desc in verbose_fixture.samples[edge_type]

def test_verbose_fixture_get_description_by_index():
    """インデックス指定による取得が正しく機能することを検証する"""
    edge_type = "protagonist_flaw"
    desc_0 = verbose_fixture.get_description_by_index(edge_type, 0)
    desc_1 = verbose_fixture.get_description_by_index(edge_type, 1)
    assert desc_0 == verbose_fixture.samples[edge_type][0]
    assert desc_1 == verbose_fixture.samples[edge_type][1]
    assert desc_0 != desc_1

def test_verbose_fixture_get_verbose_spec():
    """SharpEdgeSpec インスタンスが正しく生成されることを検証する"""
    edge_type = "sharp_conflict"
    spec = verbose_fixture.get_verbose_spec(edge_type)
    assert isinstance(spec, SharpEdgeSpec)
    assert spec.edge_type == edge_type
    assert spec.description in verbose_fixture.samples[edge_type]

def test_verbose_fixture_unknown_edge_type():
    """未知の edge_type に対するフォールバック挙動を検証する"""
    edge_type = "unknown_edge"
    desc = verbose_fixture.get_random_description(edge_type)
    assert "に関する詳細な描写" in desc
