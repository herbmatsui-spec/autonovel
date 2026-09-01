from src.services.text_chunker import split_into_paragraphs


def test_split_into_paragraphs_empty():
    """空文字・空白文字列のハンドリング検証。"""
    assert split_into_paragraphs("") == []
    assert split_into_paragraphs("   \n\n   ") == []


def test_split_into_paragraphs_basic():
    """段落区切りによる自然なチャンク分割の検証。"""
    text = (
        "第1段落。主人公は立ち上がった。\n\n"
        "第2段落。目の前には巨大なドラゴンがいた。\n\n"
        "第3段落。剣を抜き、構えた。"
    )

    chunks = split_into_paragraphs(text, max_chunk_chars=30)
    assert len(chunks) >= 2
    assert "第1段落" in chunks[0]
