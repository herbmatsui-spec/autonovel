"""6コマ要約漫画 (yonkoma) 機能のユニットテスト。

LLM 不要経路 (ヒューリスティック) とプロンプト組み立て関数を中心に検証する。
"""
from __future__ import annotations

from src.models.illustration import (
    IllustrationModel,
    IllustrationRequest,
    IllustrationType,
    SafetyLevel,
)
from src.services.illustration.prompts import (
    apply_yonkoma_safety_modifier,
    build_yonkoma_prompt,
)
from src.services.illustration.scene_service import YonkomaPlanner

SAMPLE_TEXT = (
    "古城の門前で主人公アルトは師匠の遺品を受け取る。\n\n"
    "奥へ進むと封印された魔剣が静かに輝いていた。\n\n"
    "魔剣を抜いた瞬間、館全体が轟音を立てて揺れた。\n\n"
    "影から黒衣の騎士が姿を現し、一太刀を振り下ろす。\n\n"
    "アルトは辛うじて受け止めたが、膝をついてしまう。\n\n"
    "その刹那、背後の扉が砕け散り、仲間のエレナが飛び込んできた。\n\n"
    "ふたりは顔を見合わせ、共に館を脱出することを決意する。"
)


class TestBuildYonkomaPrompt:
    def test_contains_all_six_panels(self):
        summaries = ["導入", "展開", "転換", "高潮", "余韻", "次回への引き"]
        ctx = {"title": "魔王の讃歌", "genre": "ファンタジー"}
        prompt = build_yonkoma_prompt(summaries, ctx, panels=6)

        assert "Work title: 魔王の讃歌." in prompt
        assert "epic fantasy art style" in prompt
        for i in range(1, 7):
            assert f"Panel {i}" in prompt
        assert "No text or letters in image" in prompt

    def test_panel_count_can_be_reduced(self):
        summaries = ["導入", "展開", "転換", "高潮", "余韻", "次回への引き"]
        ctx = {"title": "t", "genre": "ラブコメ"}
        prompt = build_yonkoma_prompt(summaries, ctx, panels=4)
        # panels=4 のときは Panel 5 / Panel 6 指示が出ない
        assert "Panel 4 [CLIMAX]" in prompt
        assert "Panel 5" not in prompt
        assert "Panel 6" not in prompt

    def test_long_summary_is_truncated(self):
        long_summary = "あ" * 500
        prompt = build_yonkoma_prompt(
            [long_summary, "", "", "", "", ""], {"title": "t"}, panels=6
        )
        assert "..." in prompt
        # 元の 500 文字は含まれていない
        assert "あ" * 500 not in prompt

    def test_missing_summaries_get_placeholder(self):
        prompt = build_yonkoma_prompt([""], {"title": "t"}, panels=6)
        assert "(implicit progression based on previous panel)" in prompt


class TestYonkomaSafetyModifier:
    def test_off_when_not_r15(self):
        prompt = "base prompt"
        assert apply_yonkoma_safety_modifier(prompt, SafetyLevel.BLOCK_SOME) == prompt

    def test_on_when_r15(self):
        prompt = "base prompt"
        out = apply_yonkoma_safety_modifier(prompt, SafetyLevel.R15_CONTENT)
        assert "Tasteful R15" in out
        assert "all panels" in out


class TestYonkomaPlannerHeuristic:
    def test_six_paragraphs_yields_six_summaries(self):
        planner = YonkomaPlanner()
        out = planner.plan_heuristic(SAMPLE_TEXT, panels=6)
        assert len(out) == 6
        assert all(s.strip() for s in out)

    def test_short_paragraphs_padded(self):
        text = "短い導入段落。短い結論。"
        out = YonkomaPlanner().plan_heuristic(text, panels=6)
        assert len(out) == 6

    def test_empty_text_falls_back_to_placeholder(self):
        out = YonkomaPlanner().plan_heuristic("", panels=6)
        assert out == ["(導入)"] * 6

    def test_panel_count_clamped(self):
        out = YonkomaPlanner().plan_heuristic(SAMPLE_TEXT, panels=99)
        assert len(out) == 6  # max=6
        out = YonkomaPlanner().plan_heuristic(SAMPLE_TEXT, panels=1)
        assert len(out) == 3  # min=3


class TestIllustrationRequestPanels:
    def test_default_panels_is_six(self):
        req = IllustrationRequest(
            book_id=1,
            illustration_type=IllustrationType.YONKOMA,
        )
        assert req.panels == 6

    def test_yonkoma_type_exists(self):
        assert IllustrationType.YONKOMA.value == "yonkoma"

    def test_model_auto_default(self):
        req = IllustrationRequest(
            book_id=1,
            illustration_type=IllustrationType.YONKOMA,
        )
        assert req.model == IllustrationModel.AUTO
