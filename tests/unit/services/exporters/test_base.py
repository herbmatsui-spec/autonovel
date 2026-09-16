from src.services.exporters.base import (
    normalize_newlines,
    escape_ruby_markup,
    process_image_placeholders,
    process_ruby_markup,
    process_footnotes,
    detect_unsupported_elements,
    sanitize_for_narou,
    sanitize_for_kakuyomu,
    sanitize_for_nocturne,
    sanitize_for_markdown,
    sanitize_for_plain_text,
    escape_md,
    ruby_filter,
    pagebreak_filter,
    wordcount_filter,
    BaseExporter,
    NarouExporter,
    KakuyomuExporter,
    NocturneExporter,
    PlainTextExporter,
    MarkdownExporter,
    EpubExporter,
    PdfExporter,
    get_exporter,
    list_platforms,
)

# Helper function tests

def test_normalize_newlines():
    assert normalize_newlines("") == ""
    assert normalize_newlines("hello") == "hello"
    assert normalize_newlines("hello\nworld") == "hello\nworld"
    assert normalize_newlines("hello\r\nworld") == "hello\nworld"
    assert normalize_newlines("hello\rworld") == "hello\nworld"
    assert normalize_newlines("hello\n\n\nworld") == "hello\n\nworld"
    assert normalize_newlines("hello\n\n\n\nworld") == "hello\n\nworld"
    assert normalize_newlines("hello\n\nworld\n\n\n") == "hello\n\nworld\n\n"

def test_escape_ruby_markup():
    assert escape_ruby_markup("") == ""
    assert escape_ruby_markup("|漢字《かんじ》|") == "|漢字《かんじ》|"
    assert escape_ruby_markup("rubyなし") == "rubyなし"

def test_process_image_placeholders():
    # narou
    assert process_image_placeholders("![alt](url)", "narou") == "[画像: alt]"
    assert process_image_placeholders("![alt](url \"title\")", "narou") == "[画像: alt]"
    assert process_image_placeholders("![alt](url)", "kakuyomu") == "![alt](url)"
    assert process_image_placeholders("![alt](url \"title\")", "kakuyomu") == "![alt](url \"title\")"
    assert process_image_placeholders("![alt](url)", "nocturn") == "[画像: alt]"
    assert process_image_placeholders("![alt](url)", "markdown") == "![alt](url)"
    assert process_image_placeholders("![alt](url)", "txt") == "[画像: alt]"
    # 複数
    assert process_image_placeholders("![a](u) ![b](v)", "narou") == "[画像: a] [画像: b]"
    # altなし
    assert process_image_placeholders("![](url)", "narou") == "[画像]"
    assert process_image_placeholders("![](url)", "narou") == "[画像]"

def test_process_ruby_markup():
    # narou
    assert process_ruby_markup("|漢字《かんじ》|", "narou") == "|漢字《かんじ》|"
    assert process_ruby_markup("|漢字《かんじ》|", "kakuyomu") == "|漢字《かんじ》|"
    assert process_ruby_markup("|漢字《かんじ》|", "nocturn") == "|漢字《かんじ》|"
    assert process_ruby_markup("|漢字《かんじ》|", "markdown") == "<ruby>漢字<rt>かんじ</rt></ruby>"
    assert process_ruby_markup("|漢字《かんじ》|", "txt") == "漢字"
    # rubyなし
    assert process_ruby_markup("rubyなし", "narou") == "rubyなし"
    # 複数
    assert process_ruby_markup("|あ《ア》| |い《イ》|", "narou") == "|あ《ア》| |い《イ》|"

def test_process_footnotes():
    # narou
    assert process_footnotes("^[注釈]", "narou") == "（注釈）"
    assert process_footnotes("^[注釈1]^[注釈2]", "narou") == "（注釈1）（注釈2）"
    assert process_footnotes("^[注釈]", "kakuyomu") == "[^注釈]"
    assert process_footnotes("^[注釈1]^[注釈2]", "kakuyomu") == "[^注釈1][^注釈2]"
    assert process_footnotes("^[注釈]", "nocturn") == "（注釈）"
    assert process_footnotes("^[注釈]", "markdown") == "[^注釈]"
    assert process_footnotes("^[注釈]", "txt") == "（注釈）"
    # 脚注なし
    assert process_footnotes("脚注なし", "narou") == "脚注なし"

def test_detect_unsupported_elements():
    text = "![alt](url) ^[注釈] <b>bold</b>"
    warns = detect_unsupported_elements(text, "narou")
    assert any("画像プレースホルダ" in w for w in warns)
    assert any("脚注" in w for w in warns)
    assert any("HTMLタグ" in w for w in warns)
    # kakuyomuは画像と脚注をサポートするが、HTMLはサポートしない
    warns = detect_unsupported_elements(text, "kakuyomu")
    assert not any("画像プレースホルダ" in w for w in warns)
    assert not any("脚注" in w for w in warns)
    assert any("HTMLタグ" in w for w in warns)
    # markdownはすべてサポート
    warns = detect_unsupported_elements(text, "markdown")
    assert len(warns) == 0

def test_sanitize_for_narou():
    assert sanitize_for_narou("![alt](url)") == "[画像: alt]"
    assert sanitize_for_narou("^[注釈]") == "（注釈）"
    assert sanitize_for_narou("|漢字《かんじ》|") == "|漢字《かんじ》|"
    assert sanitize_for_narou("<b>bold</b>") == "<b>bold</b>"  # HTMLは変換されない

def test_sanitize_for_kakuyomu():
    assert sanitize_for_kakuyomu("![alt](url)") == "![alt](url)"
    assert sanitize_for_kakuyomu("^[注釈]") == "[^注釈]"
    assert sanitize_for_kakuyomu("|漢字《かんじ》|") == "|漢字《かんじ》|"

def test_sanitize_for_nocturne():
    assert sanitize_for_nocturne("![alt](url)") == "[画像: alt]"
    assert sanitize_for_nocturne("^[注釈]") == "（注釈）"
    assert sanitize_for_nocturne("|漢字《かんじ》|") == "|漢字《かんじ》|"

def test_sanitize_for_markdown():
    assert sanitize_for_markdown("![alt](url)") == "![alt](url)"
    assert sanitize_for_markdown("^[注釈]") == "[^注釈]"
    assert sanitize_for_markdown("|漢字《かんじ》|") == "<ruby>漢字<rt>かんじ</rt></ruby>"
    assert sanitize_for_markdown("<b>bold</b>") == "<b>bold</b>"

def test_sanitize_for_plain_text():
    assert sanitize_for_plain_text("![alt](url)") == "[画像: alt]"
    assert sanitize_for_plain_text("^[注釈]") == "（注釈）"
    assert sanitize_for_plain_text("|漢字《かんじ》|") == "漢字"
    assert sanitize_for_plain_text("\ufeffhello") == "hello"  # BOM除去

def test_escape_md():
    input_str = "hello*world_#!"
    expected = "hello\\*world\\_\\#\\!"
    assert escape_md(input_str) == expected

def test_ruby_filter():
    assert ruby_filter("|漢字《かんじ》|") == "|漢字《かんじ》|"
    assert ruby_filter("plain") == "plain"

def test_pagebreak_filter():
    assert pagebreak_filter("narou") == "\n=====\n"
    assert pagebreak_filter("kakuyomu") == "---\n"
    assert pagebreak_filter("nocturn") == "\n---\n"
    assert pagebreak_filter("markdown") == "---\n"
    assert pagebreak_filter("txt") == "\n" + "-" * 20 + "\n"

def test_wordcount_filter():
    assert wordcount_filter("") == 0
    assert wordcount_filter("abc") == 3
    assert wordcount_filter("あいう") == 3
    assert wordcount_filter("hello world") == 11  # 空白も含む文字数

# Exporterクラスのテスト

class DummyExporter(BaseExporter):
    platform = "dummy"
    description = "ダミー"

    def export(self, novel, chapters):
        return "ダミーエクスポート"

    def export_stream(self, novel, chapters):
        yield "ダミーストリーム"

def test_base_exporter():
    exporter = DummyExporter()
    novel = {"title": "テスト", "synopsis": "テスト用の小説。"}
    chapters = [{"title": "第1話", "content": "第1話の内容。"}]
    assert exporter.export(novel, chapters) == "ダミーエクスポート"
    assert list(exporter.export_stream(novel, chapters)) == ["ダミーストリーム"]
    assert exporter._header(novel) == "# テスト\n\nテスト用の小説。\n"
    assert exporter._footer(novel) == ""
    assert exporter._format_chapter(chapters[0]) == "## 第1話\n\n第1話の内容。\n"

def test_narou_exporter():
    exporter = NarouExporter()
    novel = {"title": "テストタイトル", "synopsis": "あらすじ。", "is_adult": False}
    chapters = [
        {"title": "第1話", "content": "こんにちは世界！![img](url)"},
        {"title": "第2話", "content": "第2話。"}
    ]
    result = exporter.export(novel, chapters)
    # ヘッダーが存在することを確認
    assert "# テストタイトル\n\nあらすじ。\n" in result
    # 画像プレースホルダが変換されていることを確認
    assert "[画像: img]" in result
    assert "## 第1話\n\nこんにちは世界！[画像: img]\n" in result
    # 話の間の区切り
    assert "\n=====\n" in result
    assert "## 第2話\n\n第2話。\n" in result

def test_kakuyomu_exporter():
    exporter = KakuyomuExporter()
    novel = {"title": "テストタイトル", "synopsis": "あらすじ。", "is_adult": True}
    chapters = [
        {"title": "第1話", "content": "こんにちは世界！![img](url)"},
        {"title": "第2話", "content": "第2話。"}
    ]
    result = exporter.export(novel, chapters)
    assert "# テストタイトル\n\nあらすじ。\n\n" in result
    assert "![img](url)" in result  # 画像は保持
    assert "### 第1話\n\nこんにちは世界！![img](url)\n" in result
    assert "---\n" in result  # 話の間の区切り
    assert "### 第2話\n\n第2話。\n\n" in result
    assert "\n[R18]\n" in result  # 成年タグは最後に

def test_nocturne_exporter():
    exporter = NocturneExporter()
    novel = {"title": "テストタイトル", "synopsis": "あらすじ。", "is_adult": True}
    chapters = [
        {"title": "第1話", "content": "こんにちは世界！![img](url)"},
        {"title": "第2話", "content": "第2話。"}
    ]
    result = exporter.export(novel, chapters)
    assert "# テストタイトル\n\n" in result
    assert "[R18] 成年向けコンテンツを含みます。\n\n" in result
    assert "[画像: img]" in result  # 画像は変換
    assert "## 第1話\n\nこんにちは世界！[画像: img]\n" in result
    assert "\n---\n" in result  # 区切り
    assert "## 第2話\n\n第2話。\n\n" in result
    assert "\n[年齢確認: 18歳以上であることを確認しました]\n" in result
    assert "[官能]\n" in result

def test_plain_text_exporter():
    exporter = PlainTextExporter()
    novel = {"title": "テストタイトル", "synopsis": "あらすじ。"}
    chapters = [
        {"title": "第1話", "content": "こんにちは世界！"},
        {"title": "第2話", "content": "第2話。"}
    ]
    result = exporter.export(novel, chapters)
    assert "『テストタイトル』\n\nあらすじ：\nあらすじ。\n\n" in result
    assert "=" * 30 + "\n" in result
    assert "◆ 第1話 ◆\n\nこんにちは世界！\n\n" in result
    assert "\n" + "-" * 20 + "\n" in result  # 区切り
    assert "◆ 第2話 ◆\n\n第2話。\n\n" in result

def test_markdown_exporter():
    exporter = MarkdownExporter()
    novel = {"title": "テストタイトル", "synopsis": "あらすじ。", "tags": ["tag1", "tag2"]}
    chapters = [
        {"title": "第1話", "content": "こんにちは世界！"},
        {"title": "第2話", "content": "第2話。"}
    ]
    result = exporter.export(novel, chapters)
    # フロントマター
    assert "---\n" in result
    assert 'title: "テストタイトル"' in result
    assert 'description: "あらすじ。"' in result
    assert 'tags: [tag1, tag2]' in result
    assert "---\n\n" in result
    assert "# テストタイトル\n" in result
    assert "> あらすじ。\n\n" in result
    assert "## 第1話\n\nこんにちは世界！\n" in result
    assert "---\n" in result  # 区切り
    assert "## 第2話\n\n第2話。\n" in result

def test_epub_exporter():
    exporter = EpubExporter()
    novel = {"title": "テストタイトル", "synopsis": "あらすじ。", "tags": ["tag1"]}
    chapters = [{"title": "第1話", "content": "こんにちは世界！"}]
    result = exporter.export(novel, chapters)
    assert "---\n" in result
    assert 'title: "テストタイトル"' in result
    assert 'description: "あらすじ。"' in result
    assert 'tags: [tag1]' in result
    assert "---\n\n" in result
    assert "# テストタイトル\n" in result
    assert "> あらすじ。\n\n" in result
    assert "## 第1話\n\nこんにちは世界！\n" in result

def test_pdf_exporter():
    exporter = PdfExporter()
    novel = {"title": "テストタイトル", "synopsis": "あらすじ。"}
    chapters = [{"title": "第1話", "content": "こんにちは世界！"}]
    result = exporter.export(novel, chapters)
    assert "---\n" in result
    assert 'title: "テストタイトル"' in result
    assert 'description: "あらすじ。"' in result
    assert "---\n\n" in result
    assert "# テストタイトル\n" in result
    assert "## 第1話\n\nこんにちは世界！\n" in result

# get_exporter と list_platforms のテスト

def test_get_exporter():
    assert isinstance(get_exporter("narou"), NarouExporter)
    assert isinstance(get_exporter("kakuyomu"), KakuyomuExporter)
    assert isinstance(get_exporter("nocturne"), NocturneExporter)
    assert isinstance(get_exporter("nocturn"), NocturneExporter)  # エイリアス
    assert isinstance(get_exporter("txt"), PlainTextExporter)
    assert isinstance(get_exporter("markdown"), MarkdownExporter)
    assert isinstance(get_exporter("epub"), EpubExporter)
    assert isinstance(get_exporter("pdf"), PdfExporter)
    # 不明なものはなろうをデフォルトとする
    assert isinstance(get_exporter("unknown"), NarouExporter)

def test_list_platforms():
    platforms = list_platforms()
    platform_dict = {p["platform"]: p["description"] for p in platforms}
    assert platform_dict["narou"] == "小説家になろう（改行・ルビ・話区切りを標準整形）"
    assert platform_dict["kakuyomu"] == "カクヨム（Markdown系・R18タグ付与）"
    assert platform_dict["nocturn"] == "Nocturn Novel（官能タグ・年齢確認文言）"
    assert platform_dict["txt"] == "プレーンテキスト（シンプルな原稿テキスト）"
    assert platform_dict["markdown"] == "標準 Markdown（汎用エディタ・Obsidian等向け）"
    assert platform_dict["epub"] == "EPUB電子書籍形式"
    assert platform_dict["pdf"] == "PDFドキュメント形式"
