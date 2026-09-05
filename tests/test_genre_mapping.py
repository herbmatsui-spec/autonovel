"""UI ジャンル文字列 → preset key マッピングの単体テスト."""
from src.backend.routers.easy_mode import resolve_genre_to_preset


CASES = [
    # (genre文字列, 期待preset_key)
    ("ざまぁ・追放・無双 (R15)", "zarma"),
    ("悪役令嬢・婚約破棄", "aku_reijo"),
    ("VRMMO・ゲーム世界", "vrmmo"),
    ("追放後スローライフ", "slow_life"),
    ("ダンジョン運営", "dungeon_admin"),
    ("ループもの", "loop"),
    ("異世界テンセイ", "cheat_tensei"),
    ("現代チート", "modern_cheat"),
    ("異世界転生・バトル (R15)", "cheat_tensei"),
    ("ダークファンタジー (R15)", "cheat_tensei"),
    # マッピングなしのジャンル → None
    ("ハイファンタジー (R15)", None),
    ("未知ジャンル", None),
    ("", None),
]


def test_resolve_genre_to_preset_returns_expected_mapping():
    for genre, expected in CASES:
        got = resolve_genre_to_preset(genre)
        assert got == expected, f"genre={genre!r} expected={expected!r} got={got!r}"


def test_resolve_genre_to_preset_priority():
    """'ざまぁ' は 'loop' より優先される (順序依存のテスト)."""
    # "ループ" を含むが "ざまぁ" を含むジャンルでは zarma が優先される
    assert resolve_genre_to_preset("ざまぁループ") == "zarma"