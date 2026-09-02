"""src.easy_mode.phase3.ebook_export の単体テスト。"""
from __future__ import annotations

from src.easy_mode.phase3.ebook_export import (
    EPUB_AVAILABLE,
    PDF_AVAILABLE,
    create_ebook_exporter,
)
from src.easy_mode.pipeline import SeriesResult
from src.easy_mode.spice_guard import SpiceElement


def _make_series(genre: str = "ハイファンタジー (R15)") -> SeriesResult:
    content = "テスト本文\n\n主人公は森へ行った。\n「行くぞ」\n"
    from src.easy_mode.pipeline import EpisodeResult

    return SeriesResult(
        genre=genre,
        title="テストシリーズ",
        concept="テスト",
        total_episodes=1,
        episodes=[
            EpisodeResult(
                episode_num=1,
                title="テスト話",
                content=content,
                word_count=len(content),
                audit_score=80.0,
                audit_passed=True,
                rewrite_count=0,
                spice_elements=[SpiceElement(type="unique_metaphor", text="", position=0, priority="low")],
                metadata={},
            )
        ],
        bible={},
        plot_outline=[],
        metadata={},
    )


def test_create_ebook_exporter():
    exporter = create_ebook_exporter("ハイファンタジー (R15)", {"characters": {"archetypes": {}}, "erotic": {}})
    assert exporter is not None


def test_export_all_unknown_format_is_skipped(tmp_path):
    series = _make_series()
    exporter = create_ebook_exporter(
        "ハイファンタジー (R15)", {"characters": {"archetypes": {}}, "erotic": {}}
    )
    results = exporter.export_all(series, tmp_path, ["unknown_format"])
    assert results == {}


def test_export_all_epub_fallback(tmp_path):
    series = _make_series()
    exporter = create_ebook_exporter(
        "ハイファンタジー (R15)", {"characters": {"archetypes": {}}, "erotic": {}}
    )
    results = exporter.export_all(series, tmp_path, ["epub"])
    if not EPUB_AVAILABLE:
        # フォールバック: 空 dict または JSON ファイル
        assert isinstance(results, dict)
    else:
        assert "epub" in results
        assert results["epub"].exists()


def test_export_all_pdf_fallback(tmp_path):
    series = _make_series()
    exporter = create_ebook_exporter(
        "ハイファンタジー (R15)", {"characters": {"archetypes": {}}, "erotic": {}}
    )
    results = exporter.export_all(series, tmp_path, ["pdf"])
    if PDF_AVAILABLE:
        assert "pdf" in results
    else:
        assert isinstance(results, dict)
