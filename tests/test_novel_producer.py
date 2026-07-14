"""tests/test_novel_producer.py - NovelProducer のテスト"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.production_config import NovelProject, EpisodeResult, ProductionProgress
from src.services.novel_producer import NovelProducer
from src.services.token_tracker import TokenTracker


class TestNovelProducer:
    """NovelProducer のテスト"""

    @pytest.fixture
    def producer(self):
        """NovelProducerインスタンス"""
        tracker = TokenTracker()
        return NovelProducer(token_tracker=tracker)

    @pytest.fixture
    def sample_project(self):
        """サンプルプロジェクト"""
        return NovelProject(
            title="テスト作品",
            genre="fantasy",
            synopsis="テスト用の物語",
            keywords=["戦士", "魔法"],
            target_episodes=5,
            target_word_count_per_episode=3000
        )

    def test_init(self, producer):
        """初期化テスト"""
        assert producer.token_tracker is not None
        assert producer.episode_writer is not None
        assert producer._current_project is None
        assert producer._episodes == []

    def test_create_project(self, producer, sample_project):
        """プロジェクト作成テスト"""
        result = producer.create_project(sample_project)
        
        assert result == sample_project
        assert producer._current_project == sample_project
        assert producer._progress is not None
        assert producer._progress.total_episodes == 5

    def test_set_progress_callback(self, producer):
        """進捗コールバック設定テスト"""
        callback_called = []
        
        def callback(progress):
            callback_called.append(progress)
        
        producer.set_progress_callback(callback)
        assert producer.progress_callback is not None

    def test_get_progress(self, producer, sample_project):
        """進捗取得テスト"""
        producer.create_project(sample_project)
        
        progress = producer.get_progress()
        assert progress is not None
        assert progress.status == "idle"
        assert progress.total_episodes == 5

    def test_get_episodes_empty(self, producer):
        """エピソード一覧取得テスト（空）"""
        episodes = producer.get_episodes()
        assert episodes == []

    def test_update_progress(self, producer, sample_project):
        """進捗更新テスト"""
        producer.create_project(sample_project)
        
        producer._update_progress("running", "テスト中")
        
        assert producer._progress.status == "running"
        assert producer._progress.message == "テスト中"


class TestNovelProject:
    """NovelProject のテスト"""

    def test_create_minimal(self):
        """最小構成で作成"""
        project = NovelProject(
            title="テスト",
            genre="fantasy",
            synopsis="テスト"
        )
        assert project.target_episodes == 10
        assert project.target_word_count_per_episode == 3000
        assert project.keywords == []

    def test_create_full(self):
        """完全構成で作成"""
        project = NovelProject(
            title="覇者の帰還",
            genre="fantasy",
            synopsis="最强の戦士が覚醒する",
            keywords=["戦士", "覚醒", "覇権"],
            target_episodes=10,
            target_word_count_per_episode=3000,
            style_key="epic",
            engine_key="standard"
        )
        assert project.title == "覇者の帰還"
        assert project.target_episodes == 10
        assert len(project.keywords) == 3


class TestProductionProgress:
    """ProductionProgress のテスト"""

    def test_progress_percent(self):
        """進捗パーセント計算テスト"""
        progress = ProductionProgress(
            current_episode=3,
            total_episodes=10,
            status="running",
            completed_eps=[1, 2, 3]
        )
        assert progress.progress_percent == 30.0

    def test_is_complete(self):
        """完了判定テスト"""
        progress_complete = ProductionProgress(
            current_episode=10,
            total_episodes=10,
            status="completed",
            completed_eps=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        )
        assert progress_complete.is_complete is True
        
        progress_incomplete = ProductionProgress(
            current_episode=5,
            total_episodes=10,
            status="running",
            completed_eps=[1, 2, 3, 4, 5]
        )
        assert progress_incomplete.is_complete is False