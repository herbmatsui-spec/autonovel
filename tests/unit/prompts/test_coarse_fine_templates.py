import pytest
from pathlib import Path
import jinja2
from src.models.plot import EpisodeMacroSkeleton, PlotMacroBatch, PlotMicroBlueprint


@pytest.fixture
def jinja_env():
    templates_dir = Path(__file__).resolve().parents[3] / "prompts" / "templates"
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


class TestCoarseFineTemplates:
    def test_render_macro_skeleton(self, jinja_env):
        template = jinja_env.get_template("narrative/macro_plot_skeleton.j2")
        rendered = template.render(
            book_title="テストタイトル",
            book_genre="異世界ファンタジー",
            concept="追放からの逆転",
            ep_range_str="第1話〜第3話",
            roadmap_items=[
                {
                    "ep_num": 1,
                    "one_line_summary": "追放宣告",
                    "resolution_style": "Cheat",
                    "burned_cost_or_loot": "神槌",
                    "thematic_milestone": "覚醒",
                    "antagonist_status": "嘲笑",
                }
            ],
            schema_json="{}",
        )
        assert "テストタイトル" in rendered
        assert "追放宣告" in rendered
        assert "第1話〜第3話" in rendered
        assert "微細な会話やシーンビート（beats）はここでは一切出力しないでください" in rendered

    def test_render_macro_skeleton_empty_roadmap(self, jinja_env):
        template = jinja_env.get_template("narrative/macro_plot_skeleton.j2")
        rendered = template.render(
            book_title="空ロードマップ作品",
            ep_range_str="第1話",
            roadmap_items=[],
            schema_json="{}",
        )
        assert "空ロードマップ作品" in rendered
        assert "起承転結とテンションの波を設計してください" in rendered

    def test_render_micro_scene_expander(self, jinja_env):
        template = jinja_env.get_template("narrative/micro_scene_expander.j2")
        macro = EpisodeMacroSkeleton(
            ep_num=2,
            title="奈落の鍛冶場",
            one_line_summary="古代遺跡で神槌を振るう",
            inciting_event="魔獣の襲撃",
            climax_payoff="初の一撃粉砕",
            tension=75,
            current_chain_phase="Payoff",
            resolution_style="Cheat",
        )
        rendered = template.render(
            ep_num=2,
            macro=macro,
            previous_ending_text="奈落の暗闇に、赤い双眸が光った。",
            characters_summary="- 主人公: 表向きは冷静だが、腹の底では見返してやると誓っている",
            schema_json="{}",
        )
        assert "第2話 大局骨子" in rendered
        assert "奈落の鍛冶場" in rendered
        assert "奈落の暗闇に、赤い双眸が光った。" in rendered
        assert "Show, Don't Tell" in rendered
        assert "3シーン構成への厳格な分割" in rendered

    def test_render_micro_ep01_first_episode(self, jinja_env):
        template = jinja_env.get_template("narrative/micro_scene_expander.j2")
        macro = EpisodeMacroSkeleton(
            ep_num=1,
            title="開幕の追放",
        )
        rendered = template.render(
            ep_num=1,
            macro=macro,
            previous_ending_text="",  # 第1話なので前話なし
            characters_summary="",
            schema_json="{}",
        )
        assert "第1話 開幕演出方針" in rendered
        assert "世界観の解説は一切禁じます" in rendered
