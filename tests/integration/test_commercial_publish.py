"""
tests/integration/test_commercial_publish.py - 商用出版統合テスト
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.backend.workflows.commercial_pipeline import CommercialPipeline
from src.services.publishers import (
    NarouCredentials,
    KakuyomuCredentials,
    PublishResult,
)


class TestCommercialPipelinePublish:
    """CommercialPipeline投稿機能統合テスト"""
    
    @pytest.fixture
    def pipeline(self):
        return CommercialPipeline()
    
    @pytest.fixture
    def sample_novel(self):
        return {
            "title": "テスト小説",
            "synopsis": "これはテスト小説のあらすじです。",
            "genre": "fantasy",
            "tags": ["ファンタジー", "冒険"],
            "is_adult": False,
        }
    
    @pytest.fixture
    def sample_episodes(self):
        return [
            {"ep_num": 1, "title": "第1話", "content": "第1話の本文です。"},
            {"ep_num": 2, "title": "第2話", "content": "第2話の本文です。"},
            {"ep_num": 3, "title": "第3話", "content": "第3話の本文です。"},
        ]
    
    @pytest.fixture
    def narou_credentials(self):
        return NarouCredentials(email="test@test.com", password="password")
    
    @pytest.fixture
    def kakuyomu_credentials(self):
        return KakuyomuCredentials(api_token="test_token", user_id="user_123")
    
    @pytest.mark.asyncio
    async def test_publish_to_narou(self, pipeline, sample_novel, sample_episodes, narou_credentials):
        """なろう投稿テスト"""
        credentials = {"narou": narou_credentials}
        
        # NarouPublisherをモック
        with patch("src.backend.workflows.commercial_pipeline.get_publisher") as mock_get_pub:
            mock_publisher = AsyncMock()
            mock_publisher.authenticate = AsyncMock(return_value=True)
            mock_publisher._apply_rate_limit = AsyncMock()
            
            # 第1話はpublish、第2話以降はupdate_chapter
            mock_publisher.publish = AsyncMock(return_value=PublishResult(
                success=True,
                platform="narou",
                post_id="novel_123",
                url="https://ncode.syosetu.com/n123/",
                metadata={"novel_id": "novel_123", "episode": 1}
            ))
            mock_publisher.update_chapter = AsyncMock(return_value=PublishResult(
                success=True,
                platform="narou",
                post_id="novel_123",
                url="https://ncode.syosetu.com/n123/2/",
                metadata={"novel_id": "novel_123", "episode": 2}
            ))
            
            mock_get_pub.return_value = mock_publisher
            
            results = await pipeline._publish_to_platforms(
                novel=sample_novel,
                episodes=sample_episodes,
                platforms=["narou"],
                credentials=credentials,
            )
        
        assert "narou" in results
        narou_results = results["narou"]
        assert len(narou_results) == 3
        
        # 第1話はpublish
        assert narou_results[0].success is True
        assert narou_results[0].post_id == "novel_123"
        
        # 第2話以降はupdate_chapter
        assert narou_results[1].success is True
        assert narou_results[2].success is True
        
        # post_idがepisodesに記録される
        assert sample_episodes[0]["narou_post_id"] == "novel_123"
        assert sample_episodes[1]["narou_post_id"] == "novel_123"
        assert sample_episodes[2]["narou_post_id"] == "novel_123"
    
    @pytest.mark.asyncio
    async def test_publish_to_multiple_platforms(self, pipeline, sample_novel, sample_episodes, narou_credentials, kakuyomu_credentials):
        """複数プラットフォーム投稿テスト"""
        credentials = {
            "narou": narou_credentials,
            "kakuyomu": kakuyomu_credentials,
        }
        
        with patch("src.backend.workflows.commercial_pipeline.get_publisher") as mock_get_pub:
            # なろうモック
            narou_pub = AsyncMock()
            narou_pub.authenticate = AsyncMock(return_value=True)
            narou_pub._apply_rate_limit = AsyncMock()
            narou_pub.publish = AsyncMock(return_value=PublishResult(
                success=True, platform="narou", post_id="n123"
            ))
            narou_pub.update_chapter = AsyncMock(return_value=PublishResult(
                success=True, platform="narou", post_id="n123"
            ))
            
            # カクヨムモック
            kakuyomu_pub = AsyncMock()
            kakuyomu_pub.authenticate = AsyncMock(return_value=True)
            kakuyomu_pub._apply_rate_limit = AsyncMock()
            kakuyomu_pub.publish = AsyncMock(return_value=PublishResult(
                success=True, platform="kakuyomu", post_id="k456"
            ))
            kakuyomu_pub.update_chapter = AsyncMock(return_value=PublishResult(
                success=True, platform="kakuyomu", post_id="k456"
            ))
            
            def get_pub_side_effect(platform):
                if platform == "narou":
                    return narou_pub
                elif platform == "kakuyomu":
                    return kakuyomu_pub
                raise ValueError(f"Unknown: {platform}")
            
            mock_get_pub.side_effect = get_pub_side_effect
            
            results = await pipeline._publish_to_platforms(
                novel=sample_novel,
                episodes=sample_episodes,
                platforms=["narou", "kakuyomu"],
                credentials=credentials,
            )
        
        assert "narou" in results
        assert "kakuyomu" in results
        assert len(results["narou"]) == 3
        assert len(results["kakuyomu"]) == 3
    
    @pytest.mark.asyncio
    async def test_publish_auth_failure(self, pipeline, sample_novel, sample_episodes, narou_credentials):
        """認証失敗テスト"""
        credentials = {"narou": narou_credentials}
        
        with patch("src.backend.workflows.commercial_pipeline.get_publisher") as mock_get_pub:
            mock_publisher = AsyncMock()
            mock_publisher.authenticate = AsyncMock(return_value=False)
            mock_get_pub.return_value = mock_publisher
            
            results = await pipeline._publish_to_platforms(
                novel=sample_novel,
                episodes=sample_episodes,
                platforms=["narou"],
                credentials=credentials,
            )
        
        assert "narou" in results
        assert len(results["narou"]) == 1
        assert results["narou"][0].success is False
        assert "認証失敗" in results["narou"][0].error
    
    @pytest.mark.asyncio
    async def test_publish_partial_failure(self, pipeline, sample_novel, sample_episodes, narou_credentials):
        """部分的失敗テスト（第2話だけ失敗）"""
        credentials = {"narou": narou_credentials}
        
        with patch("src.backend.workflows.commercial_pipeline.get_publisher") as mock_get_pub:
            mock_publisher = AsyncMock()
            mock_publisher.authenticate = AsyncMock(return_value=True)
            mock_publisher._apply_rate_limit = AsyncMock()
            
            # 第1話成功、第2話失敗、第3話成功
            mock_publisher.publish = AsyncMock(return_value=PublishResult(
                success=True, platform="narou", post_id="n123"
            ))
            mock_publisher.update_chapter = AsyncMock(side_effect=[
                PublishResult(success=False, platform="narou", error="Network error"),
                PublishResult(success=True, platform="narou", post_id="n123"),
            ])
            
            mock_get_pub.return_value = mock_publisher
            
            results = await pipeline._publish_to_platforms(
                novel=sample_novel,
                episodes=sample_episodes,
                platforms=["narou"],
                credentials=credentials,
            )
        
        assert results["narou"][0].success is True
        assert results["narou"][1].success is False
        assert results["narou"][2].success is True
    
    @pytest.mark.asyncio
    async def test_run_with_publish(self, pipeline, sample_novel, sample_episodes, narou_credentials):
        """run()メソッドでdo_publish=Trueテスト"""
        credentials = {"narou": narou_credentials}
        
        # 内部メソッドをモック
        with patch.object(pipeline, "_step_plan_async") as mock_plan:
            with patch.object(pipeline, "_generate_content_async") as mock_gen:
                with patch.object(pipeline, "_publish_to_platforms") as mock_pub:
                    with patch.object(pipeline, "_create_schedule_csv") as mock_csv:
                        
                        mock_plan.return_value = {
                            "concept": "テスト",
                            "genre": "fantasy",
                            "keywords": ["ファンタジー"],
                            "target_eps": 3,
                            "target_word_count_per_episode": 3000,
                        }
                        
                        mock_gen.return_value = (sample_episodes, {})
                        mock_csv.return_value = "/tmp/schedule.csv"
                        
                        mock_pub.return_value = {
                            "narou": [
                                PublishResult(success=True, platform="narou", post_id="n123"),
                                PublishResult(success=True, platform="narou", post_id="n123"),
                                PublishResult(success=True, platform="narou", post_id="n123"),
                            ]
                        }
                        
                        result = await pipeline.run(
                            series_config={
                                "keywords": "ファンタジー",
                                "target_eps": 3,
                                "platforms": ["narou"],
                            },
                            samples=[],
                            platforms=["narou"],
                            credentials=credentials,
                            do_publish=True,
                        )
        
        assert result["publish_results"] == mock_pub.return_value
        mock_pub.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_without_publish(self, pipeline, sample_novel, sample_episodes):
        """run()メソッドでdo_publish=False（デフォルト）テスト"""
        with patch.object(pipeline, "_step_plan_async") as mock_plan:
            with patch.object(pipeline, "_generate_content_async") as mock_gen:
                with patch.object(pipeline, "_publish_to_platforms") as mock_pub:
                    with patch.object(pipeline, "_create_schedule_csv") as mock_csv:
                        
                        mock_plan.return_value = {"target_eps": 3}
                        mock_gen.return_value = (sample_episodes, {})
                        mock_csv.return_value = "/tmp/schedule.csv"
                        
                        result = await pipeline.run(
                            series_config={"keywords": "テスト"},
                            samples=[],
                            platforms=["narou"],
                            do_publish=False,
                        )
        
        assert result["publish_results"] == {}
        mock_pub.assert_not_called()


class TestCommercialPipelineRun:
    """CommercialPipeline.run()統合テスト"""
    
    @pytest.fixture
    def pipeline(self):
        return CommercialPipeline()
    
    @pytest.mark.asyncio
    async def test_run_basic(self, pipeline):
        """基本実行テスト"""
        with patch.object(pipeline, "_step_plan_async") as mock_plan:
            with patch.object(pipeline, "_generate_content_async") as mock_gen:
                with patch.object(pipeline, "_create_schedule_csv") as mock_csv:
                    
                    mock_plan.return_value = {
                        "concept": "テスト概念",
                        "genre": "fantasy",
                        "keywords": ["魔法", "冒険"],
                        "target_eps": 2,
                        "target_word_count_per_episode": 3000,
                    }
                    
                    mock_gen.return_value = (
                        [
                            {"ep_num": 1, "title": "第1話", "content": "内容1"},
                            {"ep_num": 2, "title": "第2話", "content": "内容2"},
                        ],
                        {}
                    )
                    mock_csv.return_value = "/tmp/test.csv"
                    
                    result = await pipeline.run(
                        series_config={"keywords": "魔法"},
                        samples=[],
                        platforms=["narou"],
                    )
        
        assert "bible" in result
        assert "selected" in result
        assert len(result["selected"]) == 2
        assert result["schedule_csv"] == "/tmp/test.csv"
        assert "publish_results" in result
        assert result["publish_results"] == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])