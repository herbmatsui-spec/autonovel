import pytest
from pydantic import ValidationError
from src.models.plot import (
    EpisodeMacroSkeleton,
    PlotMacroBatch,
    PlotMicroBlueprint,
    merge_macro_and_micro,
    PlotEpisode,
)
from src.models.plot import MasterSceneBlock, SceneBeatBlock


class TestMacroSkeleton:
    def test_create_macro_skeleton(self):
        skeleton = EpisodeMacroSkeleton(
            ep_num=1,
            title="追放された鍛冶師",
            one_line_summary="理不尽に追放された鍛冶師が古代の神槌を手に入れる",
            inciting_event="勇者パーティから役立たずと罵倒され追放",
            climax_payoff="奈落の底で神代の鍛冶場を発見し神槌を覚醒",
            tension=80,
            current_chain_phase="Payoff",
            resolution_style="Cheat",
            foreshadowing_plan=["FS01_god_hammer"],
        )
        assert skeleton.ep_num == 1
        assert skeleton.title == "追放された鍛冶師"
        assert skeleton.tension == 80
        assert skeleton.current_chain_phase == "Payoff"
        assert skeleton.foreshadowing_plan == ["FS01_god_hammer"]

    def test_macro_skeleton_type_coercion(self):
        # 文字列の tension が int に変換されるか
        skeleton = EpisodeMacroSkeleton(
            ep_num="2",
            tension="75",
            title="新天地へ",
        )
        assert skeleton.ep_num == 2
        assert skeleton.tension == 75

    def test_macro_batch_creation(self):
        s1 = EpisodeMacroSkeleton(ep_num=1, title="第1話")
        s2 = EpisodeMacroSkeleton(ep_num=2, title="第2話")
        batch = PlotMacroBatch(episodes=[s1, s2])
        assert len(batch.episodes) == 2
        assert batch.episodes[0].ep_num == 1
        assert batch.episodes[1].ep_num == 2

    def test_macro_batch_unwrap(self):
        # LLM が {"metadata": {"episodes": [...]}} や {"data": [...]} で返した場合のアンラップ
        raw_data = {
            "metadata": {
                "episodes": [
                    {"ep_num": 1, "title": "第1話"},
                    {"ep_num": 2, "title": "第2話"},
                ]
            }
        }
        batch = PlotMacroBatch.model_validate(raw_data)
        assert len(batch.episodes) == 2
        assert batch.episodes[0].title == "第1話"


class TestMicroBlueprint:
    def test_create_micro_blueprint(self):
        micro = PlotMicroBlueprint(
            ep_num=1,
            thought_process="冒頭300字で理不尽を叩き込み、末尾で神槌の咆哮で引く",
            detailed_blueprint="シーン1で追放、シーン2で奈落落下、シーン3で覚醒",
            scenes=[],
            bridge_from_previous="開幕のため接続なし",
            script_content="勇者「消えろ」 主人公「……後悔するなよ」",
        )
        assert micro.ep_num == 1
        assert "冒頭300字" in micro.thought_process
        assert len(micro.scenes) == 0

    def test_micro_blueprint_empty_scenes(self):
        micro = PlotMicroBlueprint(ep_num=1)
        assert micro.scenes == []

    def test_scene_beats_nested(self):
        beat = SceneBeatBlock(
            beat_type="導入",
            action_description="冷たい雨が主人公の頬を打ち付け、足元の泥が靴を濡らす。",
            sensory_keywords=["冷たい雨", "泥の感触"],
            psychology_keywords=["屈辱", "諦念"],
            target_words=200,
        )
        scene = MasterSceneBlock(
            scene_number=1,
            action="追放宣告を受ける",
            dialogue_point="お前の席はもうない",
            beats=[beat],
        )
        micro = PlotMicroBlueprint(
            ep_num=1,
            scenes=[scene],
        )
        assert len(micro.scenes) == 1
        assert len(micro.scenes[0].beats) == 1
        assert micro.scenes[0].beats[0].beat_type == "導入"
        assert "冷たい雨" in micro.scenes[0].beats[0].sensory_keywords

    def test_from_dict_parsing(self):
        data = {
            "ep_num": 3,
            "thought_process": "思考テスト",
            "detailed_blueprint": "設計図テスト",
            "scenes": [
                {
                    "scene_number": 1,
                    "action": "行動テスト",
                    "beats": [
                        {
                            "beat_type": "展開",
                            "action_description": "テスト描写詳細がここに入る",
                        }
                    ],
                }
            ],
        }
        micro = PlotMicroBlueprint.model_validate(data)
        assert micro.ep_num == 3
        assert len(micro.scenes) == 1
        assert micro.scenes[0].beats[0].action_description == "テスト描写詳細がここに入る"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            PlotMicroBlueprint()


class TestMergeModels:
    def test_merge_success(self):
        macro = EpisodeMacroSkeleton(
            ep_num=1,
            title="追放鍛冶師",
            one_line_summary="神槌覚醒",
            tension=85,
            current_chain_phase="Payoff",
            resolution_style="Cheat",
            foreshadowing_plan=["FS_HAMMER"],
        )
        micro = PlotMicroBlueprint(
            ep_num=1,
            thought_process="思考プロセス",
            detailed_blueprint="詳細設計図2000字",
            scenes=[
                MasterSceneBlock(
                    scene_number=1,
                    action="追放",
                )
            ],
        )
        merged = merge_macro_and_micro(macro, micro)
        assert isinstance(merged, PlotEpisode)
        assert merged.ep_num == 1
        assert merged.title == "追放鍛冶師"
        assert merged.detailed_blueprint == "詳細設計図2000字"
        assert merged.tension == 85
        assert len(merged.scenes) == 1

    def test_merge_ep_num_mismatch(self):
        macro = EpisodeMacroSkeleton(ep_num=1, title="第1話")
        micro = PlotMicroBlueprint(ep_num=2, title="第2話")
        with pytest.raises(ValueError, match="話数が一致しません"):
            merge_macro_and_micro(macro, micro)

    def test_extract_macro_skeleton(self):
        plot = PlotEpisode(
            ep_num=1,
            title="テストタイトル",
            one_line_summary="一行あらすじ",
            tension=70,
        )
        macro = plot.extract_macro_skeleton()
        assert isinstance(macro, EpisodeMacroSkeleton)
        assert macro.ep_num == 1
        assert macro.title == "テストタイトル"
        assert macro.tension == 70

    def test_extract_micro_blueprint(self):
        plot = PlotEpisode(
            ep_num=1,
            thought_process="思考",
            detailed_blueprint="設計図",
            scenes=[MasterSceneBlock(scene_number=1, action="シーン1")],
        )
        micro = plot.extract_micro_blueprint()
        assert isinstance(micro, PlotMicroBlueprint)
        assert micro.ep_num == 1
        assert micro.detailed_blueprint == "設計図"
        assert len(micro.scenes) == 1

    def test_roundtrip_merge(self):
        original = PlotEpisode(
            ep_num=5,
            title="決戦の前夜",
            one_line_summary="嵐の前の静けさ",
            detailed_blueprint="詳細な夜景描写と内面葛藤",
            tension=60,
            scenes=[MasterSceneBlock(scene_number=1, action="焚き火を囲む")],
        )
        macro = original.extract_macro_skeleton()
        micro = original.extract_micro_blueprint()
        restored = merge_macro_and_micro(macro, micro)
        assert restored.ep_num == original.ep_num
        assert restored.title == original.title
        assert restored.tension == original.tension
        assert restored.detailed_blueprint == original.detailed_blueprint
        assert len(restored.scenes) == len(original.scenes)
