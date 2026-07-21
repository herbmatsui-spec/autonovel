"""tests/test_erotic_mocks.py
テスト用モック官能小説の検証テスト。
"""
import pytest

from tests.fixtures.erotic_mocks import (
    count_phases,
    estimate_intensity_from_text,
    extract_intensity_from_metadata,
    get_all_mock_names,
    get_mock_metadata,
    load_mock,
)


MOCK_FILES = {
    "mock_erotic_pure_love.md": {
        "expected_intensity": 3,
        "expected_phases": {"BUILD": 1, "PEAK": 1, "AFTERGLOW": 1},
    },
    "mock_erotic_taboo.md": {
        "expected_intensity": 4,
        "expected_phases": {"BUILD": 1, "PEAK": 1, "AFTERGLOW": 1},
    },
    "mock_erotic_extreme.md": {
        "expected_intensity": 5,
        "expected_phases": {"BUILD": 1, "PEAK": 1, "AFTERGLOW": 1},
    },
}


class TestEroticMocks:
    """テスト用モック官能小説の検証。"""

    def test_all_mocks_exist(self):
        """すべてのモックファイルが存在することを確認。"""
        available = get_all_mock_names()
        for expected in MOCK_FILES.keys():
            assert expected in available, f"Missing mock: {expected}"

    @pytest.mark.parametrize(
        "filename,expected_intensity",
        [
            ("mock_erotic_pure_love.md", 3),
            ("mock_erotic_taboo.md", 4),
            ("mock_erotic_extreme.md", 5),
        ],
    )
    def test_mock_has_all_phases(self, filename, expected_intensity):
        """各モックがBUILD/PEAK/AFTERGLOWの全フェーズを持つことを確認。"""
        text = load_mock(filename)
        phases = count_phases(text)

        assert phases["BUILD"] >= 1, f"{filename}: BUILD phase missing"
        assert phases["PEAK"] >= 1, f"{filename}: PEAK phase missing"
        assert phases["AFTERGLOW"] >= 1, f"{filename}: AFTERGLOW phase missing"

    @pytest.mark.parametrize(
        "filename,expected_intensity",
        [
            ("mock_erotic_pure_love.md", 3),
            ("mock_erotic_taboo.md", 4),
            ("mock_erotic_extreme.md", 5),
        ],
    )
    def test_mock_has_metadata(self, filename, expected_intensity):
        """各モックがメタデータセクションを持ち、強度が正しいことを確認。"""
        text = load_mock(filename)
        metadata = get_mock_metadata(text)

        assert "想定強度" in metadata, f"{filename}: missing 想定強度 in metadata"
        actual_intensity = extract_intensity_from_metadata(metadata)
        assert (
            actual_intensity == expected_intensity
        ), f"{filename}: metadata intensity {actual_intensity} != expected {expected_intensity}"

    @pytest.mark.parametrize(
        "filename,expected_intensity",
        [
            ("mock_erotic_pure_love.md", 3),
            ("mock_erotic_taboo.md", 4),
            ("mock_erotic_extreme.md", 5),
        ],
    )
    def test_mock_minimum_length(self, filename, expected_intensity):
        """各モックが最低文字数を持つことを確認。"""
        text = load_mock(filename)
        min_lengths = {3: 1000, 4: 1500, 5: 2000}
        assert (
            len(text) >= min_lengths[expected_intensity]
        ), f"{filename}: too short ({len(text)} < {min_lengths[expected_intensity]})"

    @pytest.mark.parametrize(
        "filename,expected_intensity",
        [
            ("mock_erotic_pure_love.md", 3),
            ("mock_erotic_taboo.md", 4),
            ("mock_erotic_extreme.md", 5),
        ],
    )
    def test_mock_metadata_matches_expected(self, filename, expected_intensity):
        """メタデータの強度が期待値と一致することを確認。"""
        text = load_mock(filename)
        metadata = get_mock_metadata(text)
        actual = extract_intensity_from_metadata(metadata)
        assert (
            actual == expected_intensity
        ), f"{filename}: metadata intensity {actual} != expected {expected_intensity}"

    def test_mock_pure_love_has_consent_expressions(self):
        """純愛モックが同意表現を含むことを確認。"""
        text = load_mock("mock_erotic_pure_love.md")
        consent_indicators = ["好きだ", "愛してる", "幸せ", "同意"]
        found = any(indicator in text for indicator in consent_indicators)
        assert found, "Pure love mock should contain consent expressions"

    def test_mock_extreme_has_dissolution_expressions(self):
        """過激モックが溶解表現を含むことを確認。"""
        text = load_mock("mock_erotic_extreme.md")
        dissolution_indicators = ["真っ白", "溶け", "消失", "崩れ"]
        found = any(indicator in text for indicator in dissolution_indicators)
        assert found, "Extreme mock should contain dissolution expressions"

    def test_mock_taboo_has_conflict_expressions(self):
        """背徳モックが葛藤表現を含むことを確認。"""
        text = load_mock("mock_erotic_taboo.md")
        conflict_indicators = ["間違っている", "許容されない", "罪悪感", "迷い"]
        found = any(indicator in text for indicator in conflict_indicators)
        assert found, "Taboo mock should contain conflict expressions"


class TestEroticMockIntegration:
    """モックを使用した統合テスト。"""

    def test_load_all_mocks(self):
        """すべてのモックが読み込めることを確認。"""
        for filename in MOCK_FILES.keys():
            text = load_mock(filename)
            assert len(text) > 0
            assert "【BUILD フェーズ" in text
            assert "【PEAK フェーズ" in text
            assert "【AFTERGLOW フェーズ" in text

    def test_mock_phase_ordering(self):
        """各モックのフェーズが正しい順序で出現することを確認。"""
        for filename in MOCK_FILES.keys():
            text = load_mock(filename)
            build_pos = text.find("【BUILD フェーズ")
            peak_pos = text.find("【PEAK フェーズ")
            afterglow_pos = text.find("【AFTERGLOW フェーズ")

            assert build_pos < peak_pos, f"{filename}: BUILD should come before PEAK"
            assert peak_pos < afterglow_pos, f"{filename}: PEAK should come before AFTERGLOW"
