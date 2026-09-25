import pytest
import json
from prompts.manager import PromptManager
from src.models.plot import EpisodeMacroSkeleton


@pytest.mark.asyncio
async def test_build_macro_prompt():
    pm = PromptManager()
    bible_data = {
        "title": "ダンジョン鍛冶師の覚醒",
        "genre": "ファンタジー",
        "concept": "神代の神槌による無双",
        "synopsis": "追放された青年が真の力を覚醒させる",
        "mc_profile": {
            "name": "レオン",
            "surface_persona": "寡黙な鍛冶職人",
            "inner_conflict": "裏切られた怒りと信頼への恐れ",
            "iron_constraint": "不当な武器は打たない",
        },
        "full_story_roadmap": [
            {
                "ep_num": 1,
                "one_line_summary": "パーティ追放と奈落落下",
                "resolution_style": "Cheat",
                "burned_cost_or_loot": "神槌ウロボロス",
                "thematic_milestone": "覚醒",
                "antagonist_status": "嘲笑と油断",
            },
            {
                "ep_num": 2,
                "one_line_summary": "奈落からの脱出と最初の反撃",
                "resolution_style": "Logic",
                "burned_cost_or_loot": "魔獣の素材",
                "thematic_milestone": "孤高の決意",
                "antagonist_status": "異変の察知",
            },
        ],
    }

    bible_json = json.dumps(bible_data, ensure_ascii=False)
    prompt = await pm.build_macro_plot_skeleton_prompt(bible_json, [1, 2])

    assert "ダンジョン鍛冶師の覚醒" in prompt
    assert "レオン" in prompt
    assert "第1話〜第2話" in prompt
    assert "パーティ追放と奈落落下" in prompt
    assert "EpisodeMacroSkeleton" in prompt or "foreshadowing_plan" in prompt


@pytest.mark.asyncio
async def test_build_micro_prompt():
    pm = PromptManager()
    macro = EpisodeMacroSkeleton(
        ep_num=2,
        title="奈落の神鎚",
        one_line_summary="魔獣を一撃で粉砕する",
        inciting_event="奈落の主の咆哮",
        climax_payoff="神鎚の一撃",
        tension=80,
        current_chain_phase="Payoff",
        resolution_style="Cheat",
    )

    prompt = await pm.build_micro_scene_expander_prompt(
        macro_skeleton=macro,
        previous_ending_text="漆黒の闇から、紅蓮の瞳がレオンを見据えていた。",
        characters_summary="- レオン: 表向きは冷静だが、胸中に怒りの炎を宿す",
    )

    assert "第2話 大局骨子" in prompt
    assert "奈落の神鎚" in prompt
    assert "漆黒の闇から、紅蓮の瞳がレオンを見据えていた。" in prompt
    assert "Show, Don't Tell" in prompt
    assert "MasterSceneBlock" in prompt or "detailed_blueprint" in prompt
