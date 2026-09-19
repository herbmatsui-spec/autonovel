"""
Unit tests for SocialReactionGenerator.
PLAN 02: エンタメ演出強化・マルチジャンル＆配信・掲示板演出
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.prose.social_reaction_generator import SocialReactionGenerator
from src.models.social_reaction import StreamComment, ForumPost


@pytest.mark.asyncio
async def test_generate_stream_comments_success():
    """正常な配信コメント生成をテスト"""
    # モックのセットアップ
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = '''{
        "comments": [
            {"user": "ユーザー1", "text": "すげえわこれｗｗｗ", "timestamp": "2026-09-19T00:00:00"},
            {"user": "ユーザー2", "text": "同接50人突破wwww", "timestamp": "2026-09-19T00:00:01"}
        ]
    }'''
    
    generator = SocialReactionGenerator(llm=mock_llm)
    comments = await generator.generate_stream_comments("主人公がドラゴンを倒した", 2)
    
    # 結果の検証
    assert len(comments) == 2
    assert isinstance(comments[0], StreamComment)
    assert comments[0].user == "ユーザー1"
    assert "すげえわこれｗｗｗ" in comments[0].text
    assert isinstance(comments[1], StreamComment)
    assert comments[1].user == "ユーザー2"
    assert "同接50人突破wwww" in comments[1].text


@pytest.mark.asyncio
async def test_generate_stream_comments_fallback():
    """LLM失敗時のフォールバック機能をテスト"""
    # モックのセットアップ（例外を発生させる）
    mock_llm = AsyncMock()
    mock_llm.generate_text.side_effect = Exception("LLM Error")
    
    generator = SocialReactionGenerator(llm=mock_llm)
    comments = await generator.generate_stream_comments("テストシーン", 3)
    
    # フォールバックコメントが生成されることを確認
    assert len(comments) == 3
    assert all(isinstance(c, StreamComment) for c in comments)
    assert all("わああああああ" in c.text for c in comments)


@pytest.mark.asyncio
async def test_generate_forum_thread_success():
    """正常な掲示板スレッド生成をテスト"""
    # モックのセットアップ
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = '''{
        "posts": [
            {"name": "イッチ", "body": "ドラゴンをソロで倒したんだけど..."},
            {"name": "名無しさん", "body": "草"}
        ]
    }'''
    
    generator = SocialReactionGenerator(llm=mock_llm)
    posts = await generator.generate_forum_thread("主人公がドラゴンを倒した", 2)
    
    # 結果の検証
    assert len(posts) == 2
    assert isinstance(posts[0], ForumPost)
    assert posts[0].res_num == 1
    assert posts[0].name == "イッチ"
    assert "ドラゴンをソロで倒した" in posts[0].body
    assert isinstance(posts[1], ForumPost)
    assert posts[1].res_num == 2
    assert posts[1].name == "名無しさん"
    assert "草" in posts[1].body


@pytest.mark.asyncio
async def test_generate_forum_thread_fallback():
    """LLM失敗時のフォールバックスレッド機能をテスト"""
    # モックのセットアップ（例外を発生させる）
    mock_llm = AsyncMock()
    mock_llm.generate_text.side_effect = Exception("LLM Error")
    
    generator = SocialReactionGenerator(llm=mock_llm)
    posts = await generator.generate_forum_thread("テストシーン", 3)
    
    # フォールバックスレッドが生成されることを確認
    assert len(posts) == 3
    assert all(isinstance(p, ForumPost) for p in posts)
    assert all(p.body == "これはひどい... でもちょっと面白いかもｗｗｗ" for p in posts)
    assert posts[0].res_num == 1
    assert posts[1].res_num == 2
    assert posts[2].res_num == 3