"""Step 13: PlatformCopyFormatter のカクヨムスマホ最適化テスト。

字下げ無効化、カクヨム空行リズム、3行超段落自動分割、
ルビ変換（|漢字《ルビ》・《《傍点》》）の正常性を検証する。
"""

import pytest

from src.services.formatters.platform_copy_formatter import (
    FormattedChapterPayload,
    PlatformCopyFormatter,
)


class TestIndentControl:
    """Step 10: 字下げON/OFF制御のテスト。"""

    def test_kakuyomu_no_indent(self) -> None:
        """カクヨム + indent_enabled=False は行頭字下げなし。"""
        res = PlatformCopyFormatter.format_for_platform(
            "タイトル", "本文テスト", platform="kakuyomu", indent_enabled=False
        )
        assert not res.body.startswith("　")
        assert res.body == "本文テスト"

    def test_kakuyomu_with_indent(self) -> None:
        """カクヨム + indent_enabled=True（デフォルト）は字下げあり。"""
        res = PlatformCopyFormatter.format_for_platform(
            "タイトル", "本文テスト", platform="kakuyomu", indent_enabled=True
        )
        assert res.body.startswith("　")

    def test_narou_default_indent(self) -> None:
        """なろうは indent_enabled=False 指定でも引数は受け付ける（字下げは既定動作）。"""
        res = PlatformCopyFormatter.format_for_platform(
            "タイトル", "本文テスト", platform="narou", indent_enabled=False
        )
        # なろうでは indent_enabled=False の場合も字下げなしで返す
        assert not res.body.startswith("　")

    def test_narou_default_indent_enabled(self) -> None:
        """なろうのデフォルトは字下げあり。"""
        res = PlatformCopyFormatter.format_for_platform("タイトル", "本文テスト")
        assert res.body.startswith("　")

    def test_dialogue_line_never_indented(self) -> None:
        """台詞行（「開始）は indent_enabled=True でも字下げされない。"""
        res = PlatformCopyFormatter.format_for_platform(
            "タイトル", "「おはよう」", platform="kakuyomu", indent_enabled=True
        )
        assert res.body == "「おはよう」"


class TestKakuyomuLineRhythm:
    """Step 11: カクヨム専用空行リズムのテスト。"""

    def test_paragraph_separated_by_blank_line(self) -> None:
        """段落間に自然な1行空行が配置される。"""
        res = PlatformCopyFormatter.format_for_platform(
            "T", "文1\n文2", platform="kakuyomu", indent_enabled=False
        )
        assert res.body == "文1\n文2"

    def test_multiple_paragraphs_normalized(self) -> None:
        """複数段落の連続空行が正規化される。"""
        res = PlatformCopyFormatter.format_for_platform(
            "T", "段落1\n\n\n\n段落2", platform="kakuyomu", indent_enabled=False
        )
        blocks = res.body.split("\n\n")
        assert len(blocks) == 2
        assert "段落1" in blocks[0]
        assert "段落2" in blocks[1]

    def test_no_triple_newlines(self) -> None:
        """3連続以上の改行は存在しない。"""
        res = PlatformCopyFormatter.format_for_platform(
            "T", "あ\n\n\n\n\nい", platform="kakuyomu", indent_enabled=False
        )
        assert "\n\n\n" not in res.body


class TestSplitDenseParagraphs:
    """Step 12: スマホ用3行超段落自動分割のテスト。"""

    def test_dense_paragraph_split(self) -> None:
        """4文以上の段落は句点基準で分割される。"""
        res = PlatformCopyFormatter.split_dense_paragraphs("長い文。長い文。長い文。長い文。")
        assert "\n\n" in res

    def test_short_paragraph_not_split(self) -> None:
        """3文以内の段落は分割されない。"""
        res = PlatformCopyFormatter.split_dense_paragraphs("短い文。短い文。短い文。")
        assert "\n\n" not in res

    def test_custom_max_lines(self) -> None:
        """max_lines=2 で2文ごとに分割される。"""
        res = PlatformCopyFormatter.split_dense_paragraphs("一。二。三。四。", max_lines=2)
        paragraphs = res.split("\n\n")
        assert len(paragraphs) == 2

    def test_empty_text(self) -> None:
        """空文字はそのまま返る。"""
        assert PlatformCopyFormatter.split_dense_paragraphs("") == ""

    def test_no_period_text(self) -> None:
        """句点なしテキストはそのまま返る。"""
        assert PlatformCopyFormatter.split_dense_paragraphs("句点がないテキスト") == "句点がないテキスト"

    def test_content_preserved_after_split(self) -> None:
        """分割後も本文内容（句点数）が保持される。"""
        original = "文A。文B。文C。文D。文E。文F。"
        res = PlatformCopyFormatter.split_dense_paragraphs(original)
        assert res.count("。") == original.count("。")
        assert res.replace("\n", "") == original


class TestKakuyomuRuby:
    """ルビ変換（カクヨム記法）の正常性テスト。"""

    def test_kakuyomu_ruby_format(self) -> None:
        """|漢字《ルビ》形式が維持される。"""
        res = PlatformCopyFormatter.format_for_platform(
            "T", "彼は｜魔法《マジック》を使った。", platform="kakuyomu", indent_enabled=False
        )
        assert "|魔法《マジック》" in res.body

    def test_kakuyomu_bouten_format(self) -> None:
        """《《傍点》》形式が維持される。"""
        res = PlatformCopyFormatter.format_for_platform(
            "T", "これは《《重要》》だ。", platform="kakuyomu", indent_enabled=False
        )
        assert "《《重要》》" in res.body

    def test_payload_structure(self) -> None:
        """ペイロード構造が正しい。"""
        res = PlatformCopyFormatter.format_for_platform(
            " タイトル ", " 本文 ", platform="kakuyomu", indent_enabled=False
        )
        assert isinstance(res, FormattedChapterPayload)
        assert res.title == "タイトル"
        assert res.platform == "kakuyomu"
        assert res.total_characters == len(res.body)
