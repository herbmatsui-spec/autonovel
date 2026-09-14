import pytest
from src.easy_mode.phase3.ebook_export import EbookExporter, EbookMetadata

def test_ebook_exporter_initialization():
    """EbookExporter の初期化をテスト"""
    exporter = EbookExporter(genre="ファンタジー", preset={})
    assert exporter.genre == "ファンタジー"
    assert exporter.preset == {}
    assert exporter.processor is not None

def test_ebook_exporter_create_metadata():
    """メタデータ作成機能をテスト"""
    exporter = EbookExporter(genre="ファンタジー", preset={})
    # SeriesResult のモックを作成
    from src.easy_mode import SeriesResult
    series = SeriesResult(
        genre="ファンタジー",
        title="テスト小説",
        concept="テスト用のコンセプト",
        total_episodes=1,
        episodes=[],
        bible="",
        plot_outline="",
        metadata={}
    )
    metadata = exporter.create_metadata(series)
    assert metadata.title == "テスト小説"
    assert metadata.genre == "ファンタジー"
    assert "Web小説" in metadata.subject
    assert "AI生成" in metadata.subject