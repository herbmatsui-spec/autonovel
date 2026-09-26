"""プロンプト戦略のテスト（Step 19 / R-03 / R-08 / R-10）。"""

from __future__ import annotations

import pytest

from src.models.illustration import (
    IllustrationRequest,
    IllustrationType,
    SafetyLevel,
)
from src.services.illustration.config import UnifiedIllustrationConfig
from src.services.illustration.strategies import (
    CharacterStrategy,
    CoverStrategy,
    EpisodeStrategy,
    Manga24Strategy,
    Yonkoma6Strategy,
    get_strategy,
    get_strategy_class,
    is_multi_panel,
)

ALL_TYPES = list(IllustrationType)


def make_request(illo_type, **kwargs):
    params = {
        "book_id": 1,
        "illustration_type": illo_type,
        "episode_number": 1,
        "scene_text": "夜空の下、主人公は剣を抜いた。剣が光り、風が吹いた。",
        "book_context": {
            "title": "天空の城",
            "genre": "ファンタジー",
            "characters": ["タロウ"],
        },
    }
    params.update(kwargs)
    return IllustrationRequest(**params)


@pytest.fixture
def config():
    return UnifiedIllustrationConfig()


# ---- 戦略の割り当て ----


@pytest.mark.parametrize(
    "illo_type,expected",
    [
        (IllustrationType.COVER, CoverStrategy),
        (IllustrationType.CHARACTER, CharacterStrategy),
        (IllustrationType.EPISODE, EpisodeStrategy),
        (IllustrationType.YONKOMA, Yonkoma6Strategy),
        (IllustrationType.MANGA_24PANEL, Manga24Strategy),
    ],
)
def test_strategy_registry(illo_type, expected, config):
    assert get_strategy_class(illo_type) is expected
    assert isinstance(get_strategy(illo_type, config), expected)


def test_unknown_type_falls_back_to_episode(config):
    """未登録種別でも Episode 戦略へフォールバック（落ちない）。"""
    assert get_strategy_class("no-such-type") is EpisodeStrategy


# ---- R-03: 文字描画の禁止 ----


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_all_strategies_forbid_text(illo_type, config):
    """【リグレッション防止】全種別のプロンプトが文字描画を禁止している。

    画像生成モデルに文字を描かせると文字化けするため、禁止句が必須。
    """
    strategy = get_strategy(illo_type, config)
    prompt = strategy.build_prompt(make_request(illo_type, panels=24))
    assert "no text" in prompt.lower()
    assert "letters" in prompt.lower()
    assert "watermark" in strategy.build_negative_prompt(make_request(illo_type)).lower()


@pytest.mark.parametrize("illo_type", [IllustrationType.YONKOMA, IllustrationType.MANGA_24PANEL])
def test_manga_strategies_forbid_speech_bubbles(illo_type, config):
    """【リグレッション防止】漫画シートはフキダシも禁止する。"""
    strategy = get_strategy(illo_type, config)
    prompt = strategy.build_prompt(make_request(illo_type, panels=24))
    assert "no speech bubbles" in prompt.lower()
    negative = strategy.build_negative_prompt(make_request(illo_type))
    assert "single panel" in negative.lower()


# ---- R-08: R15 修飾 ----


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_r15_modifier_present_for_all_types(illo_type, config):
    """【リグレッション防止】R15_CONTENT では全種別プロンプトに R15 表現が乗る。"""
    strategy = get_strategy(illo_type, config)
    request = make_request(
        illo_type, safety_level=SafetyLevel.R15_CONTENT, panels=24
    )
    prompt = strategy.build_prompt(request)
    assert "r15" in prompt.lower()


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_non_r15_has_no_r15_modifier(illo_type, config):
    """【リグレッション防止】非R15では R15 表現を混ぜない（表現規制の混入防止）。"""
    strategy = get_strategy(illo_type, config)
    request = make_request(illo_type, safety_level=SafetyLevel.BLOCK_SOME, panels=24)
    prompt = strategy.build_prompt(request)
    assert "r15" not in prompt.lower()


# ---- R-10: panels クランプ ----


@pytest.mark.parametrize(
    "given,expected",
    [(1, 3), (3, 3), (6, 6), (24, 6), (None, 6), ("bad", 6)],
)
def test_yonkoma_panels_clamped_3_to_6(given, expected):
    """【リグレッション防止】6コマ要約のコマ数は 3..6 に収まる。"""
    assert Yonkoma6Strategy.clamp_panels(given) == expected


@pytest.mark.parametrize(
    "given,expected",
    [(1, 1), (24, 24), (30, 24), (0, 1), (None, 24)],
)
def test_manga24_panels_clamped_to_24(given, expected):
    """【リグレッション防止】24コマシートのコマ数は 1..24 に収まる。"""
    assert Manga24Strategy.clamp_panels(given) == expected


# ---- 種別ごとの内容 ----


def test_cover_uses_existing_variation_array(config):
    """表紙のカメラワークは既存定数（prompts.py）と同じものを使う。"""
    from src.services.illustration.prompts import _COVER_VARIATIONS

    strategy = CoverStrategy(config)
    for index, expected in enumerate(_COVER_VARIATIONS):
        request = make_request(IllustrationType.COVER, episode_number=index)
        assert expected in strategy.build_prompt(request)


def test_cover_respects_prompt_override(config):
    strategy = CoverStrategy(config)
    request = make_request(IllustrationType.COVER, prompt_override="CUSTOM COVER")
    assert strategy.build_prompt(request).startswith("CUSTOM COVER")


def test_character_accepts_both_key_styles(config):
    """character_name / name の両方を旧実装互換で受け付ける。"""
    strategy = CharacterStrategy(config)
    a = strategy.build_prompt(
        make_request(
            IllustrationType.CHARACTER,
            book_context={"character_name": "ハナコ", "character_description": "銀髪"},
        )
    )
    b = strategy.build_prompt(
        make_request(
            IllustrationType.CHARACTER,
            book_context={"name": "ハナコ", "appearance": "銀髪"},
        )
    )
    assert "ハナコ" in a and "ハナコ" in b
    assert "銀髪" in a and "銀髪" in b


def test_episode_truncates_long_scene(config):
    """【R-08補助】長いシーン説明は 400 文字で打ち切る。"""
    strategy = EpisodeStrategy(config)
    long_scene = "夜空の星が瞬き" * 100  # 700文字
    assert len(long_scene) > 400
    prompt = strategy.build_prompt(make_request(IllustrationType.EPISODE, scene_text=long_scene))
    assert "..." in prompt
    assert long_scene not in prompt
    assert long_scene[:400] in prompt


def test_episode_without_scene_text_uses_book_context(config):
    strategy = EpisodeStrategy(config)
    request = make_request(IllustrationType.EPISODE, scene_text="", book_context={"title": "X", "genre": "SF"})
    prompt = strategy.build_prompt(request)
    assert "Scene illustration for episode 1" in prompt
    assert "SF" in prompt


def test_manga24_prompt_has_grid_and_all_panels(config):
    strategy = Manga24Strategy(config)
    prompt = strategy.build_prompt(make_request(IllustrationType.MANGA_24PANEL, panels=24))
    assert "24 panels" in prompt
    assert "4x6 grid layout" in prompt
    for index in (1, 6, 13, 24):
        assert f"Panel {index} " in prompt
    # 実際のグリッド座標が含まれる
    assert "row1-col1" in prompt
    assert "row6-col4" in prompt


def test_manga24_does_not_repeat_six_summaries(config):
    """【R-10】24コマ要約は6個の反復ではなく、本文の異なる箇所を分散させる。"""
    strategy = Manga24Strategy(config)
    scenes = "。".join(f"第{i}番目の事件が起きた" for i in range(1, 30)) + "。"
    prompt = strategy.build_prompt(
        make_request(IllustrationType.MANGA_24PANEL, scene_text=scenes, panels=24)
    )
    distinct = {
        line.split("Scene: ", 1)[1].rstrip(".")
        for line in prompt.split("Panel ")
        if "Scene: " in line
    }
    # 24コマが概ね異なるシーンを表す（6個の繰り返しではない）
    assert len(distinct) >= 20


def test_yonkoma_uses_existing_prompt_builder(config):
    """6コマ要約は既存 build_yonkoma_prompt の出力形式を保つ。"""
    strategy = Yonkoma6Strategy(config)
    prompt = strategy.build_prompt(make_request(IllustrationType.YONKOMA, panels=6))
    assert "storyboard illustration" in prompt.lower()
    for index in range(1, 7):
        assert f"Panel {index} " in prompt


def test_yonkoma_empty_scene_uses_placeholders(config):
    strategy = Yonkoma6Strategy(config)
    prompt = strategy.build_prompt(
        make_request(IllustrationType.YONKOMA, scene_text="", panels=6)
    )
    assert "(導入)" in prompt
    assert "(次回への引き)" in prompt


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_prompts_are_non_empty_and_mention_genre_style(illo_type, config):
    strategy = get_strategy(illo_type, config)
    prompt = strategy.build_prompt(make_request(illo_type, panels=24))
    assert len(prompt) > 50
    assert "fantasy" in prompt.lower()  # ファンタジー辞書，分享のスタイルヒント


def test_is_multi_panel_helper():
    assert is_multi_panel(IllustrationType.MANGA_24PANEL) is True
    assert is_multi_panel(IllustrationType.YONKOMA) is True
    assert is_multi_panel(IllustrationType.COVER) is False
