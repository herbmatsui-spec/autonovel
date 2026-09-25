"""
E2E Integration Test for Modern Dungeon Stream Multi-Genre Writing
PLAN 02: エンタメ演出強化・マルチジャンル＆配信・掲示板演出
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.writing.opening_booster import OpeningBoosterAgent
from src.agents.writing.episode_writer import EpisodeWriter
from src.services.prose.social_reaction_generator import SocialReactionGenerator
from src.models.opening_booster import OpeningEpisodeConfig
from src.models.social_reaction import StreamComment, ForumPost


@pytest.mark.asyncio
async def test_modern_dungeon_stream_full_flow():
    """現代ダンジョン配信ジャンルの企画からコメント付き執筆までのE2Eテスト"""
    # 1. モックLLMのセットアップ - 各コンポーネント用に独立したモックを使用
    
    # OpeningBoosterAgent用のモックレスポンス（リトライ込みで十分な数を用意）
    opening_responses = [
        "底辺配信者・同接1人の絶望。未知の隠し部屋でユニークスキル覚醒。配信切り忘れで引く。",
        "同接急増・コメント欄の阿鼻叫喚。ありえないボス瞬殺。トレンド1位突入で引く。",
        "大手配信者の接触・スカウト。マイペースな無自覚配信。衝撃の次回予告で引く。",
    ] * 5  # リトライ分を含めて十分な数を用意
    
    # EpisodeWriter用のモックレスポンス
    episode_response = "第4話：ダンジョン深層への潜入。新たなスキルの組み合わせで未知のモンスターを倒す。"
    
    # SocialReactionGenerator用のモックレスポンス
    stream_comments_json = '{"comments": [{"user": "視聴者1", "text": "すげええええ！", "timestamp": "2026-09-19T00:00:00"}, {"user": "視聴者2", "text": "同接10万突破wwww", "timestamp": "2026-09-19T00:00:01"}]}'
    forum_thread_json = '{"posts": [{"name": "イッチ", "body": "ドラゴン瞬殺した配信者www"}, {"name": "名無し", "body": "草"}]}'

    # 各コンポーネント用に独立したモックLLMを作成
    opening_llm = AsyncMock()
    opening_llm.generate_text.side_effect = opening_responses
    
    episode_llm = AsyncMock()
    episode_llm.generate_text.return_value = episode_response
    
    social_llm = AsyncMock()
    social_llm.generate_text.side_effect = [stream_comments_json, forum_thread_json]

    # 2. OpeningBoosterAgent で第1〜3話を生成
    opening_agent = OpeningBoosterAgent(llm=opening_llm)

    for ep_num in [1, 2, 3]:
        config = OpeningEpisodeConfig(
            ep_num=ep_num,
            target_word_count=2500,
            inciting_incident=f"第{ep_num}話の事件",
            payoff_moment=f"第{ep_num}話の山場",
        )
        result = await opening_agent.generate_opening_episode(
            config=config,
            protagonist_name="テスト配信者",
            genre="dungeon_stream",
        )
        assert result["content"] != ""
        assert result["ep_num"] == ep_num
        assert "cliffhanger" in result
        print(f"[OK] Episode {ep_num} generated: {len(result['content'])} chars")

    # 3. EpisodeWriter で第4話を生成
    mock_context_builder = AsyncMock()
    mock_context_builder.execute.return_value = MagicMock(
        artifacts={
            "writing_context": {
                "book_id": 1,
                "ep_num": 4,
                "target_word_count": 2500,
                "genre": "dungeon_stream",
                "style_intensity": "balanced",
            }
        }
    )

    mock_prompt_manager = MagicMock()
    mock_prompt_manager.build_writing_prompt = AsyncMock(return_value="テストプロンプト")

    episode_writer = EpisodeWriter(
        llm=episode_llm,
        context_builder=mock_context_builder,
        prompt_manager=mock_prompt_manager,
    )

    ep4_context = {
        "book_id": 1,
        "ep_num": 4,
        "target_word_count": 2500,
        "genre": "dungeon_stream",
        "style_intensity": "balanced",
    }
    ep4_content = await episode_writer.write(1, 4, ep4_context)
    assert ep4_content != ""
    print(f"[OK] Episode 4 generated: {len(ep4_content)} chars")

    # 4. SocialReactionGenerator で配信コメント生成
    social_generator = SocialReactionGenerator(llm=social_llm)
    climax_text = "ありえないボス瞬殺。トレンド1位突入。"
    stream_comments = await social_generator.generate_stream_comments(climax_text, 2)
    assert len(stream_comments) == 2
    assert all(isinstance(c, StreamComment) for c in stream_comments)
    print(f"[OK] Stream comments generated: {len(stream_comments)} comments")

    # 5. 掲示板スレッド生成
    forum_posts = await social_generator.generate_forum_thread(climax_text, 2)
    assert len(forum_posts) == 2
    assert all(isinstance(p, ForumPost) for p in forum_posts)
    print(f"[OK] Forum posts generated: {len(forum_posts)} posts")

    # 6. 配信コメントブロックのフォーマット確認
    comment_block = "【配信コメント】\n" + "\n".join([f"{c.user}: {c.text}" for c in stream_comments])
    assert "【配信コメント】" in comment_block
    assert "視聴者1: すげええええ！" in comment_block
    assert "視聴者2: 同接10万突破wwww" in comment_block
    print(f"[OK] Stream comment block formatted correctly")

    # 7. 掲示板スレッドブロックのフォーマット確認
    forum_block = "【掲示板スレッド】\n" + "\n".join([f"{p.res_num}：{p.name}：{p.body}" for p in forum_posts])
    assert "【掲示板スレッド】" in forum_block
    assert "1：イッチ：ドラゴン瞬殺した配信者www" in forum_block
    assert "2：名無し：草" in forum_block
    print(f"[OK] Forum thread block formatted correctly")

    # 8. ジャンル固有のクリフハンガーキーワードが含まれることを確認
    assert "同接" in result["content"] or "配信" in result["content"]
    print("[OK] Genre-specific keywords present")

    print("\n=== E2E Test PASSED: Modern Dungeon Stream Full Flow ===")


@pytest.mark.asyncio
async def test_villainess_genre_opening():
    """悪役令嬢ジャンルの開幕テスト"""
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "婚約破棄・断罪イベントの開幕。前世記憶で華麗な逆転論破。"

    opening_agent = OpeningBoosterAgent(llm=mock_llm)
    config = OpeningEpisodeConfig(ep_num=1, target_word_count=2500, inciting_incident="断罪", payoff_moment="逆転")
    result = await opening_agent.generate_opening_episode(
        config=config,
        protagonist_name="悪役令嬢",
        genre="villainess",
    )
    assert "婚約破棄" in result["content"] or "逆転論破" in result["content"]
    print("[OK] Villainess genre opening works")


@pytest.mark.asyncio
async def test_banish_fantasy_genre_opening():
    """追放ざまぁジャンルの開幕テスト（後方互換性）"""
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "理不尽な追放・虐げの提示。未知の力で絶叫。"

    opening_agent = OpeningBoosterAgent(llm=mock_llm)
    config = OpeningEpisodeConfig(ep_num=1, target_word_count=2500, inciting_incident="追放", payoff_moment="覚醒")
    result = await opening_agent.generate_opening_episode(
        config=config,
        protagonist_name="追放者",
        genre="banish_fantasy",
    )
    assert "追放" in result["content"] or "絶叫" in result["content"]
    print("[OK] Banish fantasy genre opening works (backward compatibility)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])