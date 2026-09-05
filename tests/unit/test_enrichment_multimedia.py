# tests/unit/test_enrichment_multimedia.py
"""EnrichmentAgent マルチメディアシナリオ生成の単体テスト"""
import pytest
from src.agents.enrichment.multimedia import (
    classify_scene_type,
    render_manga_script,
    render_radio_drama,
    render_anime_storyboard,
    render_live_action_shots,
    generate_scenarios,
    SceneSegment,
)


class TestSceneClassification:
    """シーン分類のテスト"""

    def test_classify_climax(self):
        """クライマックス検出"""
        text = "最終決戦だ。クライマックスの時が来た。命懸けの戦い。"
        context = {"characters": ["主人公", "ラスボス"]}
        segments = classify_scene_type(text, context)
        assert len(segments) == 1
        assert segments[0].scene_type == "climax"

    def test_classify_battle(self):
        """バトル検出"""
        text = "剣を構えて敵に向かう。攻撃をかわし反撃する。バトルの始まりだ。"
        context = {"characters": ["主人公", "敵"]}
        segments = classify_scene_type(text, context)
        assert len(segments) == 1
        assert segments[0].scene_type == "battle"

    def test_classify_romance(self):
        """ロマンス検出"""
        text = "彼女に告白した。キスをした。愛していると伝えた。"
        context = {"characters": ["主人公", "ヒロイン"]}
        segments = classify_scene_type(text, context)
        assert len(segments) == 1
        assert segments[0].scene_type == "romance"

    def test_classify_revelation(self):
        """真実発覚検出"""
        text = "正体が判明した。真実が明かされる。秘密が暴かれた。"
        context = {"characters": ["主人公", "謎の人物"]}
        segments = classify_scene_type(text, context)
        assert len(segments) == 1
        assert segments[0].scene_type == "revelation"

    def test_classify_emotional_peak(self):
        """感情のピーク検出"""
        text = "別れの時が来た。涙が止まらない。悲劇の結末。"
        context = {"characters": ["主人公", "親友"]}
        segments = classify_scene_type(text, context)
        assert len(segments) == 1
        assert segments[0].scene_type == "emotional_peak"

    def test_no_trigger_scene(self):
        """トリガーシーンなし"""
        text = "朝食を食べた。学校へ向かう。普通の日常。"
        context = {"characters": ["主人公"]}
        segments = classify_scene_type(text, context)
        assert len(segments) == 0

    def test_tension_level(self):
        """緊張度推定"""
        text_high = "死を覚悟で剣を振るう。必死の攻撃。"
        text_low = "お茶を飲みながら会話する。"
        context = {"characters": ["主人公"]}
        
        seg_high = classify_scene_type(text_high, context)[0]
        seg_low = classify_scene_type(text_low, context)
        
        if seg_low:
            assert seg_high.tension_level >= seg_low[0].tension_level


class TestMangaScript:
    """マンガ台本レンダリングのテスト"""

    def test_render_manga_script(self):
        """マンガ台本生成"""
        segment = SceneSegment(
            scene_type="climax",
            start=0,
            end=100,
            text="主人公は剣を構えた。敵が迫る。最終決戦だ。",
            characters=["主人公", "敵将軍"],
            tension_level=9,
        )
        result = render_manga_script(segment, segment.text)
        assert result["format"] == "manga_script"
        assert "pages" in result
        assert len(result["pages"]) >= 1
        assert "panels" in result["pages"][0]
        assert result["metadata"]["key_characters"] == ["主人公", "敵将軍"]
        assert result["metadata"]["tension_level"] == 9

    def test_manga_panels_structure(self):
        """コマ構造"""
        segment = SceneSegment("battle", 0, 50, "戦う。", ["A", "B"], 7)
        result = render_manga_script(segment, segment.text)
        for page in result["pages"]:
            for panel in page["panels"]:
                assert "panel_number" in panel
                assert "visual" in panel
                assert "dialogue" in panel
                assert "sfx" in panel
                assert "camera" in panel
                assert "character_focus" in panel


class TestRadioDrama:
    """ラジオドラマ台本のテスト"""

    def test_render_radio_drama(self):
        """ラジオドラマ生成"""
        segment = SceneSegment("romance", 0, 50, "好きだ。", ["彼", "彼女"], 5)
        result = render_radio_drama(segment, segment.text)
        assert result["format"] == "radio_drama"
        assert "cues" in result
        assert len(result["cues"]) >= 1
        assert result["metadata"]["cast_count"] == 2

    def test_radio_cue_structure(self):
        """キューフォーマット"""
        segment = SceneSegment("battle", 0, 50, "戦う。", ["A"], 8)
        result = render_radio_drama(segment, segment.text)
        for cue in result["cues"]:
            assert "cue_number" in cue
            assert "type" in cue
            assert "sfx" in cue
            assert "bgm" in cue
            assert "narration" in cue
            assert "dialogue" in cue
            assert "duration_estimate_sec" in cue


class TestAnimeStoryboard:
    """アニメ絵コンテのテスト"""

    def test_render_anime_storyboard(self):
        """アニメ絵コンテ生成"""
        segment = SceneSegment("climax", 0, 50, "決戦。", ["主人公", "敵"], 10)
        result = render_anime_storyboard(segment, segment.text)
        assert result["format"] == "anime_storyboard"
        assert "cuts" in result
        assert len(result["cuts"]) >= 1
        assert result["metadata"]["total_cuts"] >= 1

    def test_anime_cut_structure(self):
        """カットフォーマット"""
        segment = SceneSegment("battle", 0, 50, "戦う。", ["A"], 7)
        result = render_anime_storyboard(segment, segment.text)
        for cut in result["cuts"]:
            assert "cut_number" in cut
            assert "duration_sec" in cut
            assert "camera" in cut
            assert "action" in cut
            assert "dialogue" in cut
            assert "background" in cut
            assert "animation_note" in cut
            assert "character_layout" in cut
            assert "effect" in cut


class TestLiveActionShots:
    """実写ショットリストのテスト"""

    def test_render_live_action_shots(self):
        """実写ショットリスト生成"""
        segment = SceneSegment("romance", 0, 50, "告白。", ["彼", "彼女"], 5)
        result = render_live_action_shots(segment, segment.text)
        assert result["format"] == "live_action_shots"
        assert "shots" in result
        assert len(result["shots"]) >= 1

    def test_shot_structure(self):
        """ショットフォーマット"""
        segment = SceneSegment("battle", 0, 50, "戦う。", ["A"], 8)
        result = render_live_action_shots(segment, segment.text)
        for shot in result["shots"]:
            assert "shot_number" in shot
            assert "scene_slug" in shot
            assert "shot_type" in shot
            assert "lens" in shot
            assert "movement" in shot
            assert "actors" in shot
            assert "vfx" in shot
            assert "dialogue" in shot
            assert "lighting" in shot
            assert "duration_sec" in shot
            assert "notes" in shot


class TestGenerateScenarios:
    """統合生成のテスト"""

    def test_generate_all_formats(self):
        """4形式すべて生成"""
        text = "最終決戦だ。主人公は剣を構える。敵将軍が迫る。命懸けの戦い。"
        context = {"characters": ["主人公", "敵将軍"]}
        results = generate_scenarios(text, context)
        assert "manga_script" in results
        assert "radio_drama" in results
        assert "anime_storyboard" in results
        assert "live_action_shots" in results

    def test_non_trigger_returns_empty(self):
        """非トリガーシーンは空"""
        text = "朝食を食べた。"
        context = {"characters": ["主人公"]}
        results = generate_scenarios(text, context)
        assert results == {}