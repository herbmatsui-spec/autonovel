from src.easy_mode.phase3.ebook_export import EbookExporter, EbookMetadata

def test_ebook_exporter_initialization(tmp_path):
    meta = EbookMetadata(title="EPUBテスト")
    exporter = EbookExporter(metadata=meta, output_dir=tmp_path)
    assert exporter.metadata.title == "EPUBテスト"
    assert exporter.output_dir == tmp_path
