"""
tests/unit/test_exporters_full.py - Exporters & Export Router の網羅テスト
"""

import pytest

from src.services.exporters.base import (
    EpubExporter,
    KakuyomuExporter,
    MarkdownExporter,
    NarouExporter,
    NocturneExporter,
    PdfExporter,
    PlainTextExporter,
    escape_md,
    escape_ruby_markup,
    get_exporter,
    list_platforms,
    normalize_newlines,
    pagebreak_filter,
    ruby_filter,
    sanitize_for_kakuyomu,
    sanitize_for_markdown,
    sanitize_for_narou,
    sanitize_for_nocturne,
    sanitize_for_plain_text,
    sanitize_for_platform,
    wordcount_filter,
)


@pytest.fixture
def sample_novel():
    return {
        "title": "テスト小説タイトル",
        "synopsis": "テストあらすじ内容です。",
        "is_adult": False,
    }


@pytest.fixture
def sample_chapters():
    return [
        {
            "ep_num": 1,
            "title": "第1話 始まり",
            "content": "朝の光が差し込む。\n\n「行くぞ！」",
        },
        {
            "ep_num": 2,
            "title": "第2話 試練",
            "content": "目の前にドラゴンが現れた。",
        },
    ]


def test_filters_and_sanitizers():
    assert normalize_newlines("a\r\nb\rc\n\n\n\nd") == "a\nb\nc\n\nd"
    assert normalize_newlines("") == ""
    assert escape_ruby_markup("|漢字《かんじ》|") == "|漢字《かんじ》|"
    assert ruby_filter("text") == "text"

    assert pagebreak_filter("narou") == "\n=====\n"
    assert pagebreak_filter("kakuyomu") == "---\n"
    assert pagebreak_filter("markdown") == "---\n"

    assert wordcount_filter("こんにちは") == 5
    assert wordcount_filter("") == 0
    assert escape_md("Hello *World* #1") == "Hello \\*World\\* \\#1"

    assert sanitize_for_narou("text\r\n") == "text\n"
    assert sanitize_for_kakuyomu("text\r\n") == "text\n"
    assert sanitize_for_nocturne("text\r\n") == "text\n"
    assert sanitize_for_markdown("text\r\n") == "text\n"
    assert sanitize_for_plain_text("\ufeffBOM text") == "BOM text"
    assert sanitize_for_platform("safe\x00text\x08") == "safetext"


def test_narou_exporter(sample_novel, sample_chapters):
    exporter = NarouExporter()
    exported = exporter.export(sample_novel, sample_chapters)
    assert sample_novel["title"] in exported
    assert "第1話 始まり" in exported
    assert "第2話 試練" in exported

    stream = list(exporter.export_stream(sample_novel, sample_chapters))
    assert len(stream) >= 2


def test_kakuyomu_exporter(sample_novel, sample_chapters):
    exporter = KakuyomuExporter()
    exported = exporter.export(sample_novel, sample_chapters)
    assert sample_novel["title"] in exported
    assert "第1話 始まり" in exported

    stream = list(exporter.export_stream(sample_novel, sample_chapters))
    assert len(stream) >= 2


def test_nocturne_exporter(sample_novel, sample_chapters):
    exporter = NocturneExporter()
    exported = exporter.export(sample_novel, sample_chapters)
    assert sample_novel["title"] in exported

    stream = list(exporter.export_stream(sample_novel, sample_chapters))
    assert len(stream) >= 2


def test_plaintext_exporter(sample_novel, sample_chapters):
    exporter = PlainTextExporter()
    exported = exporter.export(sample_novel, sample_chapters)
    assert sample_novel["title"] in exported

    stream = list(exporter.export_stream(sample_novel, sample_chapters))
    assert len(stream) >= 2


def test_markdown_exporter(sample_novel, sample_chapters):
    exporter = MarkdownExporter()
    exported = exporter.export(sample_novel, sample_chapters)
    assert sample_novel["title"] in exported

    stream = list(exporter.export_stream(sample_novel, sample_chapters))
    assert len(stream) >= 2


def test_epub_and_pdf_exporter(sample_novel, sample_chapters):
    epub_exp = EpubExporter()
    epub_out = epub_exp.export(sample_novel, sample_chapters)
    assert sample_novel["title"] in epub_out
    assert len(list(epub_exp.export_stream(sample_novel, sample_chapters))) >= 1

    pdf_exp = PdfExporter()
    pdf_out = pdf_exp.export(sample_novel, sample_chapters)
    assert sample_novel["title"] in pdf_out
    assert len(list(pdf_exp.export_stream(sample_novel, sample_chapters))) >= 1


def test_get_exporter_and_list_platforms():
    platforms = list_platforms()
    assert len(platforms) >= 5
    assert any(p["platform"] == "narou" for p in platforms)

    exp_narou = get_exporter("narou")
    assert isinstance(exp_narou, NarouExporter)

    exp_unknown = get_exporter("unknown_platform_xyz")
    assert isinstance(exp_unknown, NarouExporter)

    exp_nocturne = get_exporter("nocturne")
    assert isinstance(exp_nocturne, NocturneExporter)

    exp_nocturn = get_exporter("nocturn")
    assert isinstance(exp_nocturn, NocturneExporter)


def test_template_filters(sample_novel, sample_chapters):
    exporter = NarouExporter()
    tmpl = "タイトル: {{title}}, あらすじ: {{synopsis}}, 話: {{chapter.title}}"
    rendered = exporter.apply_template_filters(tmpl, "narou", sample_novel, sample_chapters[0])
    assert "テスト小説タイトル" in rendered
    assert "第1話 始まり" in rendered
