"""
tests/integration/test_exporter.py

機能4（出版フォーマット自動整形エクスポーター）のテスト。
各プラットフォームの整形出力とファクトリを検証する。
"""
import pytest

from src.services.exporters.base import (
    KakuyomuExporter,
    NarouExporter,
    NocturneExporter,
    get_exporter,
    list_platforms,
    sanitize_for_platform,
)


@pytest.fixture
def sample_novel():
    return {"title": "勇者の冒険", "synopsis": "世界を救う物語", "is_adult": False}


@pytest.fixture
def sample_chapters():
    return [
        {"ep_num": 1, "title": "旅立ち", "content": "主人公は村を出た。"},
        {"ep_num": 2, "title": "迷宮", "content": "迷宮で魔物と戦った。"},
    ]


def test_narou_export(sample_novel, sample_chapters):
    text = NarouExporter().export(sample_novel, sample_chapters)
    assert "勇者の冒険" in text
    assert "旅立ち" in text
    assert "迷宮" in text


def test_kakuyomu_export(sample_novel, sample_chapters):
    text = KakuyomuExporter().export(sample_novel, sample_chapters)
    assert "# 勇者の冒険" in text


def test_nocturne_export_adds_age_gate():
    novel = {"title": "T", "synopsis": "S", "is_adult": True}
    text = NocturneExporter().export(novel, [])
    assert "成年向け" in text
    assert "年齢確認" in text


def test_get_exporter_factory_and_unknown_defaults_to_narou():
    assert isinstance(get_exporter("kakuyomu"), KakuyomuExporter)
    assert isinstance(get_exporter("__unknown__"), NarouExporter)


def test_list_platforms_contains_three():
    platforms = list_platforms()
    keys = {p["platform"] for p in platforms}
    assert {"narou", "kakuyomu", "nocturn"}.issubset(keys)


def test_sanitize_removes_control_chars():
    assert sanitize_for_platform("a\x07b") == "ab"
