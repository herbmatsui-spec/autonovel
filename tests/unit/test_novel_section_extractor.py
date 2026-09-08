"""Unit tests for NovelSectionExtractor (Step 37-39)."""

import pytest
from src.agents.specialists.windowing import NovelSectionExtractor, NovelSection


def test_extractor_instantiation():
    ext = NovelSectionExtractor()
    assert ext is not None


def test_extract_opening_short_text():
    ext = NovelSectionExtractor()
    text = "吾輩は猫である。名前はまだ無い。"
    res = ext.extract_opening(text, max_chars=100)
    assert res == text


def test_extract_opening_snaps_to_sentence_end():
    ext = NovelSectionExtractor()
    # 5 sentences, each ~20 chars
    s1 = "第一の文です。"
    s2 = "第二の文がここに続きます。"
    s3 = "第三の文は少し長めに書かれています。"
    s4 = "第四の文も存在します。"
    text = s1 + s2 + s3 + s4

    # max_chars cuts somewhere inside s3
    max_len = len(s1) + len(s2) + 5
    res = ext.extract_opening(text, max_chars=max_len)
    # Should cleanly end with s2 and not cut into s3
    assert res == s1 + s2
    assert res.endswith("。")


def test_extract_ending_snaps_to_sentence_start():
    ext = NovelSectionExtractor()
    s1 = "冒頭の文です。"
    s2 = "途中の出来事が語られます。"
    s3 = "そしてクライマックスへ突入した。"
    s4 = "夜の闇の向こうで、怪しい影が笑った……。"
    text = s1 + s2 + s3 + s4

    max_len = len(s3) + len(s4) + 5
    res = ext.extract_ending(text, max_chars=max_len)
    # Should start cleanly after s2
    assert res.endswith(s4)
    assert s1 not in res


def test_extract_four_sections_short_text():
    ext = NovelSectionExtractor()
    text = "第一部。第二部。第三部。第四部。"
    sections = ext.extract_four_sections(text, section_chars=100)
    assert len(sections) == 4
    names = [s.name for s in sections]
    assert names == ["ki", "sho", "ten", "ketsu"]
    full_reconstructed = "".join(s.text for s in sections)
    assert full_reconstructed == text


def test_extract_four_sections_long_text():
    ext = NovelSectionExtractor()
    paragraphs = [f"第{i}段落のテキストです。主人公は歩き続けた。" for i in range(100)]
    long_text = "\n".join(paragraphs)
    sections = ext.extract_four_sections(long_text, section_chars=300)
    assert len(sections) == 4
    for sec in sections:
        assert len(sec.text) > 0
        assert len(sec.text) <= 500
        assert 0.0 <= sec.relative_start <= sec.relative_end <= 1.0


def test_empty_text():
    ext = NovelSectionExtractor()
    assert ext.extract_opening("") == ""
    assert ext.extract_ending("") == ""
    sections = ext.extract_four_sections("")
    assert len(sections) == 4
    assert all(s.text == "" for s in sections)
