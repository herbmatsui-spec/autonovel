"""商用縦書きEPUB 3組版ビルダー・ルビプロセッサ・縦書きCSSの単体テスト (v5.0 Step 15〜18)."""
import io
import zipfile
import pytest

from src.services.exporters.epub_vertical_styler import COMMERCIAL_VERTICAL_CSS
from src.services.exporters.epub_ruby_processor import EpubRubyProcessor
from src.services.exporters.commercial_epub_builder import PureCommercialEpubBuilder


class TestEpubVerticalStyler:
    def test_css_contains_vertical_rules(self):
        assert "writing-mode: vertical-rl;" in COMMERCIAL_VERTICAL_CSS
        assert "-webkit-writing-mode: vertical-rl;" in COMMERCIAL_VERTICAL_CSS
        assert "-epub-writing-mode: vertical-rl;" in COMMERCIAL_VERTICAL_CSS
        assert "text-emphasis-style: sesame;" in COMMERCIAL_VERTICAL_CSS
        assert "text-combine-upright: all;" in COMMERCIAL_VERTICAL_CSS


class TestEpubRubyProcessor:
    def test_ruby_conversion(self):
        text = "|勇者《ゆうしゃ》よ、目覚めよ。"
        res = EpubRubyProcessor.to_xhtml_paragraphs(text)
        assert "<ruby>勇者<rt>ゆうしゃ</rt></ruby>" in res

    def test_bouten_conversion(self):
        text = "それは《《極めて重要》》な事実だ。"
        res = EpubRubyProcessor.to_xhtml_paragraphs(text)
        assert '<span class="bouten">極めて重要</span>' in res

    def test_tcy_conversion(self):
        text = "第12話だ！本当か！？"
        res = EpubRubyProcessor.to_xhtml_paragraphs(text)
        assert '<span class="tcy">12</span>' in res
        assert '<span class="tcy">！？</span>' in res

    def test_dialogue_class(self):
        text = "「行くぞ！」\n男は立ち上がった。"
        res = EpubRubyProcessor.to_xhtml_paragraphs(text)
        assert '<p class="dialogue">「行くぞ！」</p>' in res
        assert "<p>男は立ち上がった。</p>" in res


class TestPureCommercialEpubBuilder:
    def test_build_epub_structure(self):
        builder = PureCommercialEpubBuilder()
        chapters = [
            {"title": "第1話 旅立ち", "body": "|勇者《ゆうしゃ》は歩き出した。\n「世界を救う」"},
            {"title": "第2話 試練", "body": "森の《《奥深く》》へ。"},
        ]
        epub_bytes = builder.build_epub(
            title="テスト小説",
            author="テスト著者",
            chapters=chapters,
        )

        assert len(epub_bytes) > 500

        zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
        namelist = zf.namelist()

        # EPUB 3 必須構造検証
        assert "mimetype" in namelist
        # mimetype は非圧縮・先頭でなければならない
        info = zf.getinfo("mimetype")
        assert info.compress_type == zipfile.ZIP_STORED

        assert "META-INF/container.xml" in namelist
        assert "OEBPS/content.opf" in namelist
        assert "OEBPS/styles/vertical.css" in namelist
        assert "OEBPS/chapter_1.xhtml" in namelist
        assert "OEBPS/chapter_2.xhtml" in namelist

        # 右開き (vertical-rl) の検証
        opf_content = zf.read("OEBPS/content.opf").decode("utf-8")
        assert 'page-progression-direction="rtl"' in opf_content
        assert "<dc:title>テスト小説</dc:title>" in opf_content
        assert "<dc:creator>テスト著者</dc:creator>" in opf_content

        # 第1話の本文内容
        ch1_content = zf.read("OEBPS/chapter_1.xhtml").decode("utf-8")
        assert "<ruby>勇者<rt>ゆうしゃ</rt></ruby>" in ch1_content

    def test_build_epub_with_cover(self):
        builder = PureCommercialEpubBuilder()
        dummy_cover = b"fake-cover-bytes"
        epub_bytes = builder.build_epub(
            title="表紙付き作品",
            author="著者B",
            chapters=[{"title": "第1話", "body": "本文"}],
            cover_image_bytes=dummy_cover,
        )

        zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
        namelist = zf.namelist()

        assert "OEBPS/images/cover.png" in namelist
        assert "OEBPS/cover.xhtml" in namelist
        assert zf.read("OEBPS/images/cover.png") == dummy_cover
