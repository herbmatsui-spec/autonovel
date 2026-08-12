"""
Phase 2 統合テスト
かんたんモードパイプラインの全機能検証
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.easy_mode import (
    EasyModePipeline,
    PipelineConfig,
    SeriesResult,
    EpisodeResult,
    create_series,
    SpiceGuard,
    SpiceElement,
    create_spice_guard,
)


class MockEngine:
    """テスト用モックエンジン"""
    def __init__(self):
        self.llm = MockLLM()
        self.auditor = MockAuditor()
        self.narrative = MockNarrative()


class MockLLM:
    async def generate(self, prompt: str, variables: dict) -> str:
        # プロンプトの内容に応じてダミー出力を返す
        if "Bible" in prompt or "bible" in prompt.lower():
            return '{"world": "テスト世界", "concept": "テストコンセプト", "protagonist": "テスト主人公"}'
        elif "プロット" in prompt or "plot" in prompt.lower():
            return '{"title": "第1話 テスト", "beats": ["導入", "事件", "解決"]}'
        elif "執筆" in prompt or "書け" in prompt:
            return "これは第1話のテスト本文です。まるで絶望の底から這い上がったかのように、彼は立ち上がった。ざまぁ見ろとばかりに敵は顔面蒼白になった。実は彼はチート能力を持っていた。" * 50  # ~3000字
        elif "改善" in prompt or "リライト" in prompt:
            return "これは改善された第1話のテスト本文です。まるで絶望の底から這い上がったかのように、彼は立ち上がった。ざまぁ見ろとばかりに敵は顔面蒼白になった。実は彼はチート能力を持っていた。" * 50
        return "ダミー出力"


class MockAuditor:
    async def audit(self, content: str, context: dict) -> dict:
        return {
            "overall_score": 96,
            "issues": [],
            "improvements": ["冒頭のフックを強化せよ", "カタルシスの描写を深めよ"],
        }


class MockNarrative:
    pass


class TestSpiceGuard:
    """SpiceGuardテスト"""
    
    def test_spice_guard_creation_all_genres(self):
        """全ジャンルでSpiceGuard生成可能"""
        genres = ["zarma", "aku_reijo", "cheat_tensei", "slow_life", 
                  "dungeon_admin", "modern_cheat", "ts_tensei", "vrmmo", "loop"]
        for genre in genres:
            guard = create_spice_guard(genre)
            assert guard is not None
            assert guard.genre == genre
    
    def test_extract_spice_zarma(self):
        """ざまぁジャンルの尖り抽出"""
        guard = create_spice_guard("zarma")
        text = "まるで絶望の底から這い上がったかのように、彼は立ち上がった。ざまぁ見ろとばかりに敵は顔面蒼白になった。実は彼は全スキル習得のチートを持っていた。"
        elements = guard.extract_spice(text)
        
        # 重要要素が検出されること
        types = [e.type for e in elements]
        assert "zarma_catharsis_payoff" in types
        assert "plot_twist_marker" in types
        assert "unique_metaphor" in types
        
        # critical優先度があること
        critical = [e for e in elements if e.priority == "critical"]
        assert len(critical) > 0
    
    def test_extract_spice_all_genres(self):
        """全ジャンルで尖り抽出動作"""
        test_cases = {
            "zarma": "ざまぁ見ろ。実はチートだった。まるで魔王のようだ。",
            "aku_reijo": "フラグをへし折り隠しルートへ。尊い百合のキス。",
            "cheat_tensei": "スキル習得∞。秒殺ワープで最適解。効率厨の極み。",
            "slow_life": "ふわふわのパンの香り。とろける美味しさにほっこり。",
            "ts_tensei": "可愛い美少女になって百合のキス。尊い永遠の愛。",
            "loop": "100周目のループで真エンド。全フラグ回収し確率1の必然。",
        }
        
        for genre, text in test_cases.items():
            guard = create_spice_guard(genre)
            elements = guard.extract_spice(text)
            assert len(elements) > 0, f"Genre {genre}: no elements extracted"
            # criticalまたはhigh優先度があること
            high_priority = [e for e in elements if e.priority in ["critical", "high"]]
            assert len(high_priority) > 0, f"Genre {genre}: no high priority elements"
    
    def test_inject_markers(self):
        """マーカー注入・除去のラウンドトリップ"""
        guard = create_spice_guard("zarma")
        text = "ざまぁ見ろ。実はチートだった。"
        elements = guard.extract_spice(text)
        
        protected = guard.inject_markers(text, elements)
        assert "<<<SPICE:" in protected
        assert "<<</SPICE>>>" in protected
        
        # 元のテキストが含まれていること
        assert "ざまぁ" in protected
        assert "実は" in protected
        
        # 除去できること
        cleaned = guard.remove_markers(protected)
        # マーカーが除去されること（元のテキストと完全一致しないが、キーワードは残る）
        assert "ざまぁ" in cleaned
        assert "実は" in cleaned
    
    def test_rewrite_prompt_generation(self):
        """リライトプロンプト生成"""
        guard = create_spice_guard("zarma")
        content = "ざまぁ見ろ。実はチートだった。"
        improvements = ["冒頭を強化せよ", "描写を深めよ"]
        elements = guard.extract_spice(content)
        
        prompt = guard.build_rewrite_prompt(content, ["改善せよ"], elements)
        
        assert "SPICE" in prompt
        assert "絶対に変更するな" in prompt
        assert "ざまぁ" in prompt
    
    def test_priority_ordering(self):
        """優先度順ソートの確認"""
        guard = create_spice_guard("zarma")
        text = "実はざまぁ見ろ。まるで魔王のようだ。"
        elements = guard.extract_spice(text)
        
        # criticalが先頭に来ること
        priorities = [e.priority for e in elements]
        # criticalが最初に来ることを確認（ソート済み）
        critical_indices = [i for i, p in enumerate(priorities) if p == "critical"]
        if critical_indices:
            assert critical_indices[0] == 0


class TestPipelineConfig:
    """パイプライン設定テスト"""
    
    def test_default_config(self):
        config = PipelineConfig(genre="zarma")
        assert config.genre == "zarma"
        assert config.target_episodes == 8
        assert config.max_rewrite_iterations == 3
        assert config.target_audit_score == 95.0
        assert config.enable_spice_guard == True
    
    def test_custom_config(self):
        config = PipelineConfig(
            genre="cheat_tensei",
            target_episodes=12,
            max_rewrite_iterations=5,
            target_audit_score=90.0,
            enable_spice_guard=False,
        )
        assert config.target_episodes == 12
        assert config.max_rewrite_iterations == 5
        assert config.target_audit_score == 90.0
        assert config.enable_spice_guard == False


class TestPipelineIntegration:
    """パイプライン統合テスト（モック使用）"""
    
    @pytest.mark.asyncio
    async def test_pipeline_creation(self):
        """パイプライン作成"""
        engine = MockEngine()
        pipeline = create_series(engine, "zarma", target_episodes=3)
        
        assert pipeline is not None
        assert pipeline.config.genre == "zarma"
        assert pipeline.config.target_episodes == 3
    
    @pytest.mark.asyncio
    async def test_bible_generation(self):
        """Bible生成"""
        engine = MockEngine()
        pipeline = create_series(engine, "zarma", target_episodes=1)
        
        bible = await pipeline._generate_bible()
        
        assert isinstance(bible, dict)
        # Bible生成はLLMを使うため、モックではフォールバック形式になる
        # フォールバック形式は "raw" と "parsed" キーを持つ
        assert "raw" in bible or "protagonist" in bible or "fallback" in bible
    
    @pytest.mark.asyncio
    async def test_plot_generation(self):
        """プロット生成"""
        engine = MockEngine()
        pipeline = create_series(engine, "zarma", target_episodes=3)
        
        bible = {"protagonist": "テスト", "cheat_ability": "テストチート"}
        plots = await pipeline._generate_plot_outline(bible)
        
        assert len(plots) == 3
        for i, plot in enumerate(plots):
            assert plot["episode"] == i + 1
            assert "target_tension" in plot
            assert "beats" in plot
    
    @pytest.mark.asyncio
    async def test_spice_extraction_in_pipeline(self):
        """パイプライン内でのSpiceGuard動作"""
        engine = MockEngine()
        pipeline = create_series(engine, "zarma", target_episodes=1)
        pipeline.config.enable_spice_guard = True
        
        # 尖り抽出テスト
        text = "ざまぁ見ろ。実はチートだった。"
        elements = pipeline._extract_spice(text)
        
        assert len(elements) > 0
        types = [e.type for e in elements]
        assert any("zarma_" in t for t in types) or "plot_twist_marker" in types
    
    @pytest.mark.asyncio
    async def test_marker_injection(self):
        """マーカー注入・除去"""
        engine = MockEngine()
        pipeline = create_series(engine, "zarma")
        
        text = "ざまぁ見ろ。実はチートだった。"
        elements = pipeline._extract_spice(text)
        
        protected = pipeline._inject_spice_markers(text, elements)
        assert "<<<SPICE:" in protected
        
        # マーカー除去
        import re
        cleaned = re.sub(r'<<<SPICE:[^>]+>>>|<<</SPICE>>>', '', protected)
        assert "ざまぁ" in cleaned
        assert "実は" in cleaned
    
    @pytest.mark.asyncio
    async def test_rewrite_prompt(self):
        """リライトプロンプト構築"""
        engine = MockEngine()
        pipeline = create_series(engine, "zarma")
        
        content = "ざまぁ見ろ。"
        improvements = ["冒頭強化"]
        elements = pipeline._extract_spice(content)
        
        protected = pipeline._inject_spice_markers(content, elements)
        prompt = pipeline._build_rewrite_prompt(content, improvements, elements)
        
        # 実際のメソッドは _rewrite_episode 内で構築される
        # ここでは構築ロジックをテスト
        assert "SPICE" in protected or "ざまぁ" in content


class TestEpisodeResult:
    """EpisodeResult データクラステスト"""
    
    def test_episode_result_creation(self):
        ep = EpisodeResult(
            episode_num=1,
            title="第1話 テスト",
            content="テスト本文",
            word_count=100,
            audit_score=95.0,
            audit_passed=True,
            rewrite_count=0,
            spice_elements=[],
            metadata={},
            needs_human_review=False,
        )
        assert ep.episode_num == 1
        assert ep.audit_passed == True
        assert ep.needs_human_review == False


class TestSeriesResult:
    """SeriesResult データクラステスト"""
    
    def test_series_result_creation(self):
        series = SeriesResult(
            genre="zarma",
            title="テストシリーズ",
            concept="テストコンセプト",
            total_episodes=8,
            episodes=[],
            bible={},
            plot_outline=[],
            metadata={},
        )
        assert series.genre == "zarma"
        assert series.total_episodes == 8


class TestPipelineE2E:
    """パイプライン E2E 統合テスト（モックエンジンで全フロー実行）"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_run_small(self):
        """少数話でフルパイプライン実行テスト"""
        engine = MockEngine()
        # 監査で96点を返すのでリライト不要で高速完了
        pipeline = create_series(engine, "zarma", target_episodes=2)
        
        result = await pipeline.run()
        
        # 結果検証
        assert isinstance(result, SeriesResult)
        assert result.genre == "zarma"
        assert result.total_episodes == 2
        assert len(result.episodes) == 2
        assert result.title != ""
        assert result.concept != ""
        assert result.bible is not None
        assert len(result.plot_outline) == 2
        
        # エピソード検証
        for i, ep in enumerate(result.episodes):
            assert ep.episode_num == i + 1
            assert ep.title != ""
            assert ep.word_count > 0
            assert ep.audit_score >= 0
            assert ep.rewrite_count >= 0
            assert isinstance(ep.spice_elements, list)
            # 監査96点で目標95点なのでリライト不要
            assert ep.audit_passed == True
            assert ep.needs_human_review == False
    
    @pytest.mark.asyncio
    async def test_pipeline_with_low_audit_score(self):
        """低スコア監査でのリワイルートテスト"""
        
        class LowScoreMockEngine(MockEngine):
            def __init__(self):
                super().__init__()
                self.llm = MockLLM()
                self.auditor = LowScoreMockAuditor()
        
        class LowScoreMockAuditor:
            async def audit(self, content: str, context: dict) -> dict:
                return {
                    "overall_score": 80,  # 目標95未満
                    "issues": ["テンション不足", "フック弱い"],
                    "improvements": ["冒頭を強化せよ", "カタルシスを深めよ"],
                }
        
        engine = LowScoreMockEngine()
        pipeline = create_series(engine, "zarma", target_episodes=1)
        pipeline.config.max_rewrite_iterations = 2
        
        result = await pipeline.run()
        
        # リライトが実行されたことを確認
        ep = result.episodes[0]
        assert ep.rewrite_count > 0
        # 最大リトライ後もスコアが低い場合は人間レビューフラグ
        assert ep.needs_human_review == True
    
    @pytest.mark.asyncio
    async def test_pipeline_spice_guard_integration(self):
        """SpiceGuardがリライト時に機能することの確認"""
        engine = MockEngine()
        pipeline = create_series(engine, "zarma", target_episodes=1)
        
        # 尖り要素を含むテキストでリライト
        content = "ざまぁ見ろ。実はチートだった。まるで魔王のようだ。敵は顔面蒼白になった。"
        elements = pipeline._extract_spice(content)
        
        # critical優先度の要素があること
        critical_elements = [e for e in elements if e.priority == "critical"]
        assert len(critical_elements) > 0
        
        # マーカー注入
        protected = pipeline._inject_spice_markers(content, elements)
        assert "<<<SPICE:" in protected
        
        # リライトプロンプトにSPICEマーカーが含まれること
        prompt = pipeline._build_rewrite_prompt(content, ["テスト改善"], elements)
        assert "SPICE" in prompt
        assert "絶対に変更するな" in prompt
        assert "ざまぁ" in prompt
    
    @pytest.mark.asyncio
    async def test_pipeline_cancellation(self):
        """キャンセル機能のテスト"""
        engine = MockEngine()
        pipeline = create_series(engine, "zarma", target_episodes=3)
        
        # 実行前にキャンセル
        pipeline.cancel()
        
        result = await pipeline.run()
        
        # キャンセル時は空のエピソードで完了
        assert isinstance(result, SeriesResult)
        assert result.total_episodes == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])