"""
Phase 3 統合テスト
IFルート・メディアミックス・電子書籍・資産化パックの全機能検証
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.easy_mode import (
    EpisodeResult,
    SeriesResult,
)
from src.easy_mode.phase3 import (
    AssetPackMetadata,
    AudioDramaScriptGenerator,
    BranchCondition,
    ConditionOperator,
    EbookMetadata,
    EpubGenerator,
    IFRouteGraph,
    MangaScriptGenerator,
    MediaFormat,
    MediaScript,
    MobiGenerator,
    PdfGenerator,
    RouteChoice,
    VideoScriptGenerator,
    create_asset_pack_generator,
    create_ebook_exporter,
    create_if_route_system,
    create_media_mix_exporter,
)


class MockEngine:
    def __init__(self):
        self.llm = MockLLM()
        self.auditor = MockAuditor()
        self.narrative = MockNarrative()


class MockLLM:
    async def generate(self, prompt: str, variables: dict) -> str:
        if "Bible" in prompt or "bible" in prompt.lower():
            return '{"world": "テスト世界", "concept": "テストコンセプト", "protagonist": "テスト主人公"}'
        elif "プロット" in prompt or "plot" in prompt.lower():
            return '{"title": "第1話 テスト", "beats": ["導入", "事件", "解決"]}'
        elif "執筆" in prompt or "書け" in prompt:
            return "これはテスト本文です。" * 100
        elif "改善" in prompt or "リライト" in prompt:
            return "これは改善されたテスト本文です。" * 100
        return "ダミー出力"


class MockAuditor:
    async def audit(self, content: str, context: dict) -> dict:
        return {
            "overall_score": 96,
            "issues": [],
            "improvements": ["冒頭のフックを強化せよ"],
        }


class MockNarrative:
    pass


def create_test_series_result() -> SeriesResult:
    """テスト用SeriesResult作成"""
    episodes = []
    for i in range(1, 4):
        ep = EpisodeResult(
            episode_num=i,
            title=f"第{i}話 テストタイトル",
            content=f"これは第{i}話の本文です。" * 50,
            word_count=200,
            audit_score=95.0,
            audit_passed=True,
            rewrite_count=0,
            spice_elements=[],
            metadata={"plot": {"is_catharsis": i == 2}}
        )
        episodes.append(ep)

    return SeriesResult(
        genre="zarma",
        title="テストシリーズ",
        concept="テストコンセプト：追放された最強が無双する",
        total_episodes=3,
        episodes=episodes,
        bible={
            "world": "ファンタジー世界",
            "protagonist": "テスト主人公",
            "cheat_ability": "全スキル習得",
            "catharsis_target": "元パーティ",
            "characters": {
                "archetypes": {
                    "protagonist": {
                        "name_pattern": "テスト主人公（剣聖）",
                        "role": "主人公",
                        "speech_patterns": {
                            "first_person": "俺",
                            "tone": "クール"
                        }
                    }
                }
            }
        },
        plot_outline=[
            {"episode": 1, "title": "第1話 追放", "is_catharsis": False},
            {"episode": 2, "title": "第2話 覚醒", "is_catharsis": True},
            {"episode": 3, "title": "第3話 ざまぁ", "is_catharsis": True}
        ],
        metadata={"synopsis": {"hook": "追放された剣聖が無双でざまぁする"}}
    )


class TestIFRoutes:
    """IFルートテスト"""

    def test_branch_condition_evaluation(self):
        """分岐条件評価テスト"""
        cond = BranchCondition(
            variable="flags.hidden_unlocked",
            operator=ConditionOperator.EQUALS,
            value=True
        )

        assert cond.evaluate({"flags": {"hidden_unlocked": True}}) == True
        assert cond.evaluate({"flags": {"hidden_unlocked": False}}) == False
        assert cond.evaluate({}) == False

    def test_branch_condition_operators(self):
        """各演算子テスト"""
        test_cases = [
            (ConditionOperator.EQUALS, 5, 5, True),
            (ConditionOperator.EQUALS, 5, 3, False),
            (ConditionOperator.NOT_EQUALS, 5, 3, True),
            (ConditionOperator.GREATER_THAN, 10, 5, True),
            (ConditionOperator.LESS_THAN, 3, 5, True),
            (ConditionOperator.GREATER_EQUAL, 5, 5, True),
            (ConditionOperator.LESS_EQUAL, 5, 5, True),
            (ConditionOperator.CONTAINS, "hello world", "world", True),
            (ConditionOperator.NOT_CONTAINS, "hello", "world", True),
        ]

        for op, var_val, cond_val, expected in test_cases:
            cond = BranchCondition("test", op, cond_val)
            result = cond.evaluate({"test": var_val})
            assert result == expected, f"{op}: {var_val} vs {cond_val}"

    def test_route_choice_availability(self):
        """選択肢利用可能判定テスト"""
        choice = RouteChoice(
            id="test",
            text="テスト",
            conditions=[
                BranchCondition("flags.a", ConditionOperator.EQUALS, True)
            ],
            target_node_id="next"
        )

        assert choice.is_available({"flags": {"a": True}}) == True
        assert choice.is_available({"flags": {"a": False}}) == False
        assert choice.is_available({}) == False

    def test_route_choice_effects(self):
        """選択肢副作用テスト"""
        choice = RouteChoice(
            id="test",
            text="テスト",
            target_node_id="next",
            effects={"flags.new_flag": True, "variables.score": 100}
        )

        context = {"flags": {}, "variables": {}}
        new_context = choice.apply_effects(context)

        assert new_context["flags"]["new_flag"] == True
        assert new_context["variables"]["score"] == 100
        # 元のコンテキストは不変
        assert "new_flag" not in context["flags"]

    def test_if_route_generation(self):
        """IFルートグラフ生成テスト"""
        series = create_test_series_result()
        preset = {"characters": {"archetypes": {}}}

        graph = create_if_route_system("zarma", series, preset)

        assert isinstance(graph, IFRouteGraph)
        assert graph.entry_node_id == "prologue"
        assert len(graph.nodes) > 0

        # プロローグノード存在
        prologue = graph.get_node("prologue")
        assert prologue is not None
        assert prologue.branch_type.value == "choice"
        assert len(prologue.choices) > 0

        # エピソードノード存在
        for ep_num in range(1, 4):
            main_node = graph.get_node(f"ep{ep_num}_main")
            assert main_node is not None, f"ep{ep_num}_main not found"
            assert main_node.episode_num == ep_num

    def test_if_route_validation(self):
        """IFルート検証テスト"""
        series = create_test_series_result()
        preset = {"characters": {"archetypes": {}}}

        graph = create_if_route_system("zarma", series, preset)
        errors = graph.validate()

        # 重大なエラーがないこと
        critical_errors = [e for e in errors if "Entry node" in e or "missing node" in e]
        assert len(critical_errors) == 0, f"Critical errors: {critical_errors}"

    def test_if_route_player(self):
        """IFルートプレイヤーテスト"""
        from src.easy_mode.phase3.if_routes import IFRoutePlayer

        series = create_test_series_result()
        preset = {"characters": {"archetypes": {}}}

        graph = create_if_route_system("zarma", series, preset)
        player = IFRoutePlayer(graph)

        # 初期状態
        state = player.get_state()
        assert state["current_node"]["id"] == "prologue"
        assert len(state["available_choices"]) > 0

        # 選択実行
        choice_id = state["available_choices"][0]["id"]
        success = player.make_choice(choice_id)
        assert success == True

        # 状態更新確認
        new_state = player.get_state()
        assert new_state["current_node"]["id"] != "prologue"
        assert len(new_state["context"]["history"]) == 1

    def test_genre_specific_routes(self):
        """ジャンル別ルート生成テスト"""
        series = create_test_series_result()

        for genre in ["zarma", "aku_reijo", "loop", "cheat_tensei"]:
            preset = {"characters": {"archetypes": {}}}
            graph = create_if_route_system(genre, series, preset)

            assert graph.entry_node_id == "prologue"
            prologue = graph.get_node("prologue")
            assert prologue is not None

            # ジャンル別選択肢の存在確認
            choice_ids = [c.id for c in prologue.choices]
            if genre == "loop":
                assert any("true_route" in cid for cid in choice_ids)
            elif genre == "aku_reijo":
                assert any("flag_avoid" in cid for cid in choice_ids)


class TestMediaMix:
    """メディアミックステスト"""

    def test_manga_script_generation(self):
        """漫画台本生成テスト"""
        series = create_test_series_result()
        preset = {"style": {}, "characters": {"archetypes": {}}}

        generator = MangaScriptGenerator("zarma", preset)
        episode = series.episodes[0]

        script = generator.generate(episode, series)

        assert isinstance(script, MediaScript)
        assert script.format == MediaFormat.MANGA
        assert script.episode_num == 1
        assert len(script.panels) > 0
        assert script.title == "テストシリーズ 第1話"

        # パネル構造確認
        for panel in script.panels:
            assert panel.number > 0
            assert panel.description
            assert isinstance(panel.dialogue, list)
            assert isinstance(panel.sfx, list)

    def test_audio_drama_generation(self):
        """音声ドラマ台本生成テスト"""
        series = create_test_series_result()
        preset = {"characters": {"archetypes": {}}, "erotic": {}}

        generator = AudioDramaScriptGenerator("zarma", preset)
        episode = series.episodes[0]

        script = generator.generate(episode, series)

        assert script.format == MediaFormat.AUDIO_DRAMA
        assert len(script.voice_lines) > 0

        # キャスト要件確認
        meta = script.metadata
        assert "cast_requirements" in meta
        assert "characters" in meta["cast_requirements"]

    def test_video_script_generation(self):
        """動画台本生成テスト"""
        series = create_test_series_result()
        preset = {}

        generator = VideoScriptGenerator("zarma", preset)
        episode = series.episodes[0]

        script = generator.generate(episode, series)

        assert script.format == MediaFormat.VIDEO
        assert len(script.shots) > 0

        # ショット構造確認
        for shot in script.shots:
            assert shot.number > 0
            assert shot.duration > 0
            assert shot.visual_description
            assert shot.transition in ["cut", "fade_out"]

    def test_media_mix_exporter(self):
        """メディアミックス一括エクスポーターテスト"""
        series = create_test_series_result()
        preset = {"style": {}, "characters": {"archetypes": {}}, "erotic": {}}

        exporter = create_media_mix_exporter("zarma", preset)
        episode = series.episodes[0]

        scripts = exporter.export_all(episode, series)

        assert MediaFormat.MANGA in scripts
        assert MediaFormat.AUDIO_DRAMA in scripts
        assert MediaFormat.VIDEO in scripts

        # 保存テスト
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = exporter.save_all(scripts, Path(tmpdir))
            assert len(saved) == 3
            for fmt, path in saved.items():
                assert path.exists()


class TestEbookExport:
    """電子書籍エクスポートテスト"""

    def test_ebook_metadata_creation(self):
        """メタデータ作成テスト"""
        series = create_test_series_result()
        preset = {}

        exporter = create_ebook_exporter("zarma", preset)
        metadata = exporter.create_metadata(
            series,
            author="テスト著者",
            tags=["テスト"]
        )

        assert isinstance(metadata, EbookMetadata)
        assert metadata.title == "テストシリーズ"
        assert metadata.author == "テスト著者"
        assert metadata.genre == "zarma"
        assert "テスト" in metadata.tags

    def test_ebook_content_processor(self):
        """コンテンツ処理テスト"""
        from src.easy_mode.phase3.ebook_export import EbookContentProcessor

        processor = EbookContentProcessor("zarma")
        series = create_test_series_result()

        chapters = processor.create_chapters(series)

        # プロローグ + 3話 + エピローグ = 5チャプター
        assert len(chapters) >= 3

        # HTMLフォーマット確認
        for ch in chapters:
            assert "<p>" in ch.content
            assert ch.word_count > 0

    def test_css_generation(self):
        """CSS生成テスト"""
        from src.easy_mode.phase3.ebook_export import EbookContentProcessor

        processor = EbookContentProcessor("zarma")
        css = processor.generate_css()

        assert "dialogue" in css
        assert "monologue" in css
        assert "emphasis" in css
        assert "cover" in css
        assert "colophon" in css

    def test_epub_generator_mock(self):
        """EPUB生成モックテスト"""
        # ebooklibがなくてもクラスがインポートできることを確認
        assert EpubGenerator is not None

    def test_pdf_generator_mock(self):
        """PDF生成モックテスト"""
        assert PdfGenerator is not None

    def test_mobi_generator_mock(self):
        """MOBI生成モックテスト"""
        assert MobiGenerator is not None


class TestAssetPack:
    """資産化パックテスト"""

    def test_asset_pack_metadata(self):
        """メタデータテスト"""
        metadata = AssetPackMetadata(
            pack_id="test_pack",
            title="テスト",
            genre="zarma",
            episode_count=3,
            total_words=600
        )

        assert metadata.pack_id == "test_pack"
        assert metadata.title == "テスト"
        assert metadata.genre == "zarma"

        data = metadata.to_dict()
        assert data["pack_id"] == "test_pack"
        assert "created_at" in data

    def test_asset_pack_generation_structure(self):
        """パック生成構造テスト（モック）"""
        series = create_test_series_result()
        preset = {
            "style": {},
            "characters": {"archetypes": {}},
            "erotic": {},
            "marketing": {"catchphrase_templates": ["{title} - 最高！"]}
        }

        generator = create_asset_pack_generator("zarma", preset)

        # コンポーネント初期化確認
        generator._init_components(series)

        assert generator.if_generator is not None
        assert generator.media_exporter is not None
        assert generator.ebook_exporter is not None

    def test_promo_materials_generation(self):
        """プロモーション素材生成テスト"""
        series = create_test_series_result()
        preset = {
            "marketing": {"catchphrase_templates": ["{title} - 最高！"]}
        }

        generator = create_asset_pack_generator("zarma", preset)
        generator._init_components(series)

        with tempfile.TemporaryDirectory() as tmpdir:
            promo_dir = Path(tmpdir) / "promo"
            promo_dir.mkdir()

            files = generator._generate_promo_materials(series, promo_dir)

            assert "synopsis_long.txt" in files
            assert "synopsis_short.txt" in files
            assert "catchphrases.txt" in files
            assert "character_introductions.txt" in files
            assert "keywords.txt" in files
            assert "sns_posts.json" in files
            assert "press_release.txt" in files

            # ファイル存在確認
            for fname in files:
                assert (promo_dir / fname).exists()

    def test_synopsis_generation(self):
        """あらすじ生成テスト"""
        series = create_test_series_result()
        preset = {}

        generator = create_asset_pack_generator("zarma", preset)
        generator._init_components(series)

        long_synopsis = generator._generate_synopsis(series, long=True)
        short_synopsis = generator._generate_synopsis(series, long=False)

        assert "テストシリーズ" in long_synopsis
        assert "ざまぁ" in long_synopsis or "無双" in long_synopsis
        assert "テストシリーズ" in short_synopsis

    def test_keywords_generation(self):
        """キーワード生成テスト"""
        series = create_test_series_result()
        preset = {}

        generator = create_asset_pack_generator("zarma", preset)
        generator._init_components(series)

        keywords = generator._generate_keywords(series)

        assert "テストシリーズ" in keywords
        assert "zarma" in keywords
        assert "Web小説" in keywords
        assert "完結済み" in keywords
        assert any("ざまぁ" in k or "無双" in k for k in keywords)

    def test_checksum_calculation(self):
        """チェックサム計算テスト"""
        import hashlib

        generator = create_asset_pack_generator("zarma", {})

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()

            # テストファイル作成
            (test_dir / "file1.txt").write_text("hello")
            (test_dir / "file2.txt").write_text("world")
            subdir = test_dir / "sub"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("test")

            checksums = generator._calculate_checksums(test_dir)

            assert "file1.txt" in checksums
            assert "file2.txt" in checksums
            assert "sub/file3.txt" in checksums

            # 正確性確認
            expected1 = hashlib.sha256(b"hello").hexdigest()[:16]
            assert checksums["file1.txt"] == expected1


class TestPhase3Integration:
    """Phase 3 統合テスト"""

    def test_full_pipeline_to_asset_pack(self):
        """フルパイプライン→資産化パック統合テスト"""
        series = create_test_series_result()
        preset = {
            "style": {},
            "characters": {"archetypes": {}},
            "erotic": {},
            "marketing": {"catchphrase_templates": ["{title} - 最高！"]}
        }

        generator = create_asset_pack_generator("zarma", preset)
        generator._init_components(series)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # 各コンポーネント個別テスト
            # 1. IFルート
            graph = generator.if_generator.generate_from_series(series)
            assert graph.entry_node_id == "prologue"

            # 2. メディアミックス
            scripts = generator.media_exporter.export_all(
                series.episodes[0], series
            )
            assert len(scripts) == 3

            # 3. 電子書籍メタデータ
            metadata = generator.ebook_exporter.create_metadata(series)
            assert metadata.title == "テストシリーズ"

            # 4. プロモ素材
            promo_dir = output_dir / "promo"
            promo_dir.mkdir()
            promo_files = generator._generate_promo_materials(series, promo_dir)
            assert len(promo_files) >= 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
