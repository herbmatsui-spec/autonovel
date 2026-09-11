import io
import zipfile
import pytest
from src.services.exporters.epub_commercial_builder import CommercialEpubBuilder


def test_commercial_epub_builder():
    builder = CommercialEpubBuilder()
    novel_meta = {
        "title": "テスト作品",
        "author": "テスト作家",
        "publisher": "AutoNovel出版",
    }
    chapters = [
        {
            "title": "第1話 はじまり",
            "content": "「行くぞ」と｜勇者《ゆうしゃ》は《《決心》》した。\n第12魔導部隊へ進む。",
        },
        {
            "title": "第2話 激闘",
            "content": "敵が現れた!? すぐさま迎撃せよ!!",
        },
    ]

    epub_bytes = builder.build_commercial_epub(novel_meta, chapters)
    assert len(epub_bytes) > 500

    # ZIPとして解凍可能か検証
    with zipfile.ZipFile(io.BytesIO(epub_bytes), "r") as zf:
        namelist = zf.namelist()
        # 1. 規格必須: mimetype が最先頭
        assert namelist[0] == "mimetype"
        assert zf.read("mimetype") == b"application/epub+zip"

        # 2. 必須構造
        assert "META-INF/container.xml" in namelist
        assert "item/standard.opf" in namelist
        assert "item/nav.xhtml" in namelist
        assert "item/toc.ncx" in namelist
        assert "item/style/vertical.css" in namelist
        assert "item/xhtml/p-001.xhtml" in namelist
        assert "item/xhtml/p-002.xhtml" in namelist

        # 3. 縦書き指定およびルビの含有確認
        p1 = zf.read("item/xhtml/p-001.xhtml").decode("utf-8")
        assert "class=\"vrtl\"" in p1
        assert "<ruby>勇者<rt>ゆうしゃ</rt></ruby>" in p1
        assert '<span class="bouten">決心</span>' in p1
        assert '<span class="tcy">12</span>' in p1

        # 4. OPFの縦書き指定確認
        opf = zf.read("item/standard.opf").decode("utf-8")
        assert 'page-progression-direction="rtl"' in opf


def test_large_book_epub_build():
    """パフォーマンステスト: 50話を瞬時に生成可能か (Step 59)"""
    builder = CommercialEpubBuilder()
    chapters = [
        {"title": f"第{i}話", "content": "本文テスト。" * 50}
        for i in range(1, 51)
    ]
    epub_bytes = builder.build_commercial_epub({"title": "大長編"}, chapters)
    assert len(epub_bytes) > 2000
