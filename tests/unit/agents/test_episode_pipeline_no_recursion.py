"""
Unit tests for EpisodePipeline to verify no infinite recursion.
PLAN 02: エンタメ演出強化・マルチジャンル＆配信・掲示板演出
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.episode_pipeline import EpisodePipeline


@pytest.mark.asyncio
async def test_episode_pipeline_no_recursion():
    """無限再帰が発生しないことを保証するモック単体テスト"""
    # モックエージェントを作成（_write_single_episode_coreをモック）
    mock_agent = AsyncMock()
    # 1話あたり500文字を返すように設定
    mock_agent._write_single_episode_core.side_effect = [
        500,  # 第1話
        500,  # 第2話
    ]
    
    # EpisodePipelineを作成
    pipeline = EpisodePipeline(mock_agent)
    
    # レポーターモックを作成
    mock_reporter = AsyncMock()
    
    # 1話から2話までを実行（合計2話）
    total_chars, failed_episodes = await pipeline.run(
        book_id=1,
        start_ep=1,
        end_ep=2,
        passion=1.0,
        target_word_count=2500,
        is_easy_mode=False,
        reporter=mock_reporter,
        branch_id=1,
    )
    
    # 結果の検証
    assert total_chars == 1000  # 500 + 500
    assert len(failed_episodes) == 0  # 失敗がないこと
    
    # _write_single_episode_coreが正確に2回呼ばれたことを確認
    assert mock_agent._write_single_episode_core.call_count == 2
    
    # 呼び出し引数の検証
    calls = mock_agent._write_single_episode_core.call_args_list
    assert calls[0][1]['ep_num'] == 1  # 第1話の呼び出し
    assert calls[1][1]['ep_num'] == 2  # 第2話の呼び出し
    
    # 全ての呼び出しで同じbook_idとbranch_idであることを確認
    for call in calls:
        assert call[1]['book_id'] == 1
        assert call[1]['branch_id'] == 1


@pytest.mark.asyncio
async def test_episode_pipeline_with_failures():
    """失敗ケースでも無限再帰が発生しないことをテスト"""
    # モックエージェントを作成
    mock_agent = AsyncMock()
    # 1話目は成功、2話目は例外を発生させる
    mock_agent._write_single_episode_core.side_effect = [
        500,  # 第1話成功
        Exception("Network error"),  # 第2話失敗
    ]
    
    # EpisodePipelineを作成
    pipeline = EpisodePipeline(mock_agent)
    
    # レポーターモックを作成
    mock_reporter = AsyncMock()
    
    # 1話から2話までを実行
    total_chars, failed_episodes = await pipeline.run(
        book_id=1,
        start_ep=1,
        end_ep=2,
        passion=1.0,
        target_word_count=2500,
        is_easy_mode=False,
        reporter=mock_reporter,
        branch_id=1,
    )
    
    # 結果の検証
    assert total_chars == 500  # 1話目のみ成功
    assert len(failed_episodes) == 1  # 1件失敗
    assert failed_episodes[0]["ep_num"] == 2  # 第2話が失敗
    assert "Network error" in failed_episodes[0]["error_message"]
    
    # _write_single_episode_coreが正確に2回呼ばれたことを確認（失敗しても呼び出しはされる）
    assert mock_agent._write_single_episode_core.call_count == 2