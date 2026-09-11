from src.services.exporters.ruby_parser import parse_bouten, parse_ruby_to_xhtml
from src.services.exporters.tcy_formatter import apply_tatechuyoko
from src.services.exporters.epub_content_builder import EpubContentBuilder


def test_ruby_parsing():
    text = "｜魔導《まどう》と漢字《かんじ》"
    res = parse_ruby_to_xhtml(text)
    assert "<ruby>魔導<rt>まどう</rt></ruby>" in res
    assert "<ruby>漢字<rt>かんじ</rt></ruby>" in res


def test_bouten_parsing():
    text = "これは《《極秘事項》》だ。"
    res = parse_bouten(text)
    assert '<span class="bouten">極秘事項</span>' in res


def test_tatechuyoko():
    text = "第12話!? まさか99%か!!"
    res = apply_tatechuyoko(text)
    assert '<span class="tcy">12</span>' in res
    assert '<span class="tcy">!?</span>' in res
    assert '<span class="tcy">99</span>' in res
    assert '<span class="tcy">!!</span>' in res


def test_chapter_xhtml_build():
    xhtml = EpubContentBuilder.build_chapter_xhtml(
        chapter_title="第1章 旅立ち",
        content="「行くぞ」と｜勇者《ゆうしゃ》は《《決意》》した。\n第10部隊へ合流する。",
        chapter_index=1,
    )
    assert 'class="vrtl"' in xhtml
    assert "<ruby>勇者<rt>ゆうしゃ</rt></ruby>" in xhtml
    assert '<span class="bouten">決意</span>' in xhtml
    assert '<span class="tcy">10</span>' in xhtml
    assert '<p class="dialogue">' in xhtml
