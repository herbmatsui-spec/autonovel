# manual_processor/tests/test_text_processor.py
import pytest
from pathlib import Path
from unittest.mock import Mock

from src.text_processor import (
    combine_ocr_results,
    clean_extracted_text,
    normalize_japanese_text,
    extract_keywords,
    split_into_sentences,
    remove_duplicate_lines,
    Section
)
from src.ocr_processor import OCRResult

class TestCombineOCRResults:
    """OCR結果結合関数のテスト"""

    def test_combine_empty_results(self):
        """空のリストを結合すると空文字が返ること"""
        result = combine_ocr_results([])
        assert result == ""

    def test_combine_single_result(self):
        """単一のOCR結果を結合するとテキストがそのまま返ること"""
        ocr_result = OCRResult(text="テストテキスト", confidence=0.9, page_number=1, bounding_boxes=[])
        result = combine_ocr_results([ocr_result])
        assert result == "テストテキスト"

    def test_combine_multiple_results(self):
        """複数のOCR結果を正しく結合すること"""
        ocr_results = [
            OCRResult(text="ページ1", confidence=0.8, page_number=1, bounding_boxes=[]),
            OCRResult(text="ページ2", confidence=0.9, page_number=2, bounding_boxes=[]),
            OCRResult(text="ページ3", confidence=0.7, page_number=3, bounding_boxes=[])
        ]
        result = combine_ocr_results(ocr_results)
        assert "ページ1" in result
        assert "ページ2" in result
        assert "ページ3" in result

    def test_combine_unsorted_results(self):
        """順序が保たれること（ページ番号でソートされる）"""
        ocr_results = [
            OCRResult(text="ページ3", confidence=0.7, page_number=3, bounding_boxes=[]),
            OCRResult(text="ページ1", confidence=0.8, page_number=1, bounding_boxes=[]),
            OCRResult(text="ページ2", confidence=0.9, page_number=2, bounding_boxes=[])
        ]
        result = combine_ocr_results(ocr_results)
        # ページ1のテキストが最初に来ること
        assert result.index("ページ1") < result.index("ページ2")
        assert result.index("ページ2") < result.index("ページ3")

    def test_combine_with_empty_text(self):
        """空のテキストを含む結果を正しく処理すること"""
        ocr_results = [
            OCRResult(text="テスト", confidence=0.8, page_number=1, bounding_boxes=[]),
            OCRResult(text="", confidence=0.0, page_number=2, bounding_boxes=[]),
            OCRResult(text="続き", confidence=0.9, page_number=3, bounding_boxes=[])
        ]
        result = combine_ocr_results(ocr_results)
        assert "テスト" in result
        assert "続き" in result

class TestCleanExtractedText:
    """テキストクリーニング関数のテスト"""

    def test_clean_empty_text(self):
        """空のテキストをクリーニングしても空文字が返ること"""
        result = clean_extracted_text("")
        assert result == ""

    def test_clean_removes_control_characters(self):
        """制御文字を除去すること"""
        text = "テスト\x00\x01\x02テキスト"
        result = clean_extracted_text(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result

    def test_clean_removes_fullwidth_space(self):
        """全角スペースを半角スペースに変換すること"""
        text = "テスト　スペース"
        result = clean_extracted_text(text)
        assert " " in result  # 半角スペース
        assert "　" not in result  # 全角スペースなし

    def test_clean_normalizes_whitespace(self):
        """連続する空白を正規化すること"""
        text = "テスト    スペース   複数"
        result = clean_extracted_text(text)
        assert "    " not in result  # 連続スペースなし
        assert result == "テスト スペース 複数"

    def test_clean_strips_lines(self):
        """各行の先頭・末尾の空白を除去すること"""
        text = "  テスト  \n  行  \n  末尾  "
        result = clean_extracted_text(text)
        assert result == "テスト\n行\n末尾"

    def test_clean_limits_line_breaks(self):
        """連続改行を制限すること"""
        text = "テスト\n\n\n\n\n続き"
        result = clean_extracted_text(text)
        # 4つ以上の改行は3つに制限される
        assert "\n\n\n" in result

class TestNormalizeJapaneseText:
    """日本語正規化関数のテスト"""

    def test_normalize_empty_text(self):
        """空のテキストを正規化しても空文字が返ること"""
        result = normalize_japanese_text("")
        assert result == ""

    def test_convert_fullwidth_alphanumeric(self):
        """全角英数字を半角に変換すること"""
        text = "ＡＢＣａｂｃ１２３"
        result = normalize_japanese_text(text)
        assert "ABC" in result
        assert "abc" in result
        assert "123" in result
        assert "Ａ" not in result
        assert "Ｂ" not in result

    def test_preserves_japanese_characters(self):
        """日本語文字はそのまま保持されること"""
        text = "こんにちは世界"
        result = normalize_japanese_text(text)
        assert "こんにちは世界" in result

class TestExtractKeywords:
    """キーワード抽出関数のテスト"""

    def test_extract_empty_text(self):
        """空のテキストの場合は空リストを返すこと"""
        result = extract_keywords("")
        assert result == []

    def test_extract_with_max_keywords(self):
        """指定された最大数以下のキーワードを返すこと"""
        text = "テスト テスト サンプル サンプル デモ デモ アイテム"
        result = extract_keywords(text, max_keywords=3)
        assert len(result) <= 3

    def test_extract_filters_stop_words(self):
        """ストップワードは除外されること"""
        text = "の は を た が で て と し れ さ"
        result = extract_keywords(text, max_keywords=10)
        for word in result:
            assert word not in ['の', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ']

    def test_extract_ignores_short_words(self):
        """2文字未満の単語は除外されること"""
        text = "あ い う え お かきくけこ"
        result = extract_keywords(text, max_keywords=10)
        for word in result:
            assert len(word) >= 2

class TestSplitIntoSentences:
    """文分割関数のテスト"""

    def test_split_empty_text(self):
        """空のテキストの場合は空リストを返すこと"""
        result = split_into_sentences("")
        assert result == []

    def test_split_japanese_sentences(self):
        """日本語の文を正しく分割すること"""
        text = "これはテストです。これは二つ目です。"
        result = split_into_sentences(text)
        assert len(result) == 2
        assert "これはテストです" in result[0]
        assert "これは二つ目です" in result[1]

    def test_split_mixed_sentences(self):
        """日本語と英語の混在テキストを正しく分割すること"""
        text = "これはテストです。This is a test. これは三つ目です。"
        result = split_into_sentences(text)
        assert len(result) == 3

class TestRemoveDuplicateLines:
    """重複行削除関数のテスト"""

    def test_remove_duplicates_empty(self):
        """空のテキストを処理しても空文字が返ること"""
        result = remove_duplicate_lines("")
        assert result == ""

    def test_remove_duplicates_preserves_order(self):
        """重複を削除しつつ元の順序を維持すること"""
        text = "行1\n行2\n行1\n行3\n行2"
        result = remove_duplicate_lines(text)
        lines = result.split('\n')
        assert lines == ["行1", "行2", "行3"]

    def test_remove_duplicates_no_change(self):
        """重複がない場合は元のテキストがほぼそのまま返ること"""
        text = "行1\n行2\n行3"
        result = remove_duplicate_lines(text)
        assert result == text

class TestSection:
    """Section データクラスのテスト"""

    def test_section_creation(self):
        """セクションが正しく作成されること"""
        section = Section(title="テスト", content="内容")
        assert section.title == "テスト"
        assert section.content == "内容"
        assert section.subsections == []

    def test_section_with_subsections(self):
        """サブセクションを持つセクションの作成"""
        subsection = Section(title="小見出し", content="小内容")
        section = Section(title="大見出し", content="内容", subsections=[subsection])
        assert len(section.subsections) == 1
        assert section.subsections[0].title == "小見出し"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])