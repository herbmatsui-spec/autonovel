from src.easy_mode.phase3.ebook_export import EbookMetadata

def test_ebook_metadata_defaults():
    meta = EbookMetadata(title="テスト覇権小説")
    assert meta.title == "テスト覇権小説"
    assert meta.author == "AI Novel Engine"
    assert meta.language == "ja"

def test_ebook_metadata_custom():
    meta = EbookMetadata(
        title="カスタム小説",
        author="作家名",
        language="en",
        publisher="テスト出版"
    )
    assert meta.author == "作家名"
    assert meta.publisher == "テスト出版"
