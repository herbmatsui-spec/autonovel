"""
tests/test_safe_replace.py
SafeReplacer のユニットテスト。
二重置換問題が解消されていることを保証する。
"""
from src.services.safe_replace import SafeReplacer


class TestSafeReplacer:
    """SafeReplacer のテストスイート"""

    def test_basic_replacement(self):
        """基本的な単一置換"""
        replacer = SafeReplacer({"A": "B"})
        assert replacer.replace("A") == "B"

    def test_multiple_replacements(self):
        """複数パターンの同時置換"""
        replacer = SafeReplacer({"A": "X", "B": "Y"})
        assert replacer.replace("AB") == "XY"

    def test_no_double_replacement(self):
        """二重置換の防止: 値が別キーと衝突しても再置換されない"""
        replacer = SafeReplacer({
            "抱く": "肌を重ねる",
            "肌を重ねる": "二人の夜を過ごす",
        })
        result = replacer.replace("彼は彼女を抱く")
        assert result == "彼は彼女を肌を重ねる"
        assert "二人の夜を過ごす" not in result

    def test_empty_text(self):
        """空文字列入力"""
        replacer = SafeReplacer({"A": "B"})
        assert replacer.replace("") == ""

    def test_no_match(self):
        """マッチしない文字列"""
        replacer = SafeReplacer({"A": "B"})
        assert replacer.replace("XYZ") == "XYZ"

    def test_empty_mappings(self):
        """空のマッピング"""
        replacer = SafeReplacer({})
        assert replacer.replace("テスト") == "テスト"

    def test_unicode_replacement(self):
        """日本語置換"""
        replacer = SafeReplacer({"セックス": "二人の夜"})
        assert replacer.replace("セックスする") == "二人の夜する"

    def test_partial_word_match(self):
        """部分文字列マッチ"""
        replacer = SafeReplacer({"胸": "柔らかな起伏"})
        assert replacer.replace("胸が触れた") == "柔らかな起伏が触れた"

    def test_multiple_same_pattern(self):
        """同一パターンの複数出現"""
        replacer = SafeReplacer({"キス": "唇を重ねる"})
        assert replacer.replace("キスしてキス") == "唇を重ねるして唇を重ねる"

    def test_chain_prevention_extensive(self):
        """3段チェーンの防止"""
        replacer = SafeReplacer({
            "A": "B",
            "B": "C",
            "C": "D",
        })
        assert replacer.replace("A") == "B"
        assert replacer.replace("B") == "C"
        assert replacer.replace("ABC") == "BCD"
