import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.writing.opening_booster import OpeningBoosterAgent
from src.models.opening_booster import OpeningEpisodeConfig


@pytest.mark.asyncio
async def test_opening_booster_multigenre_prompt_construction():
    """ジャンルごとに適切なプロンプトが構築されることをテスト"""
    # モックのセットアップ
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "生成されたコンテンツ"
    
    agent = OpeningBoosterAgent(llm=mock_llm)
    
    # ダンジョンストリームジャンルの第1話プロンプトテスト
    config = OpeningEpisodeConfig(ep_num=1, target_word_count=2000, inciting_incident="未知の隠し部屋発見", payoff_moment="スキル覚醒")
    result = await agent.build_prompt(config, genre="dungeon_stream")
    
    # ダンジョンストリーム特有の指示が含まれていることを確認
    assert "底辺配信者" in result
    assert "隠し部屋" in result
    assert "配信切り忘れ" in result
    
    # 悪役令嬢ジャンルの第1話プロンプトテスト
    result = await agent.build_prompt(config, genre="villainess")
    
    # 悪役令嬢特有の指示が含まれていることを確認
    assert "貴族の娘" in result
    assert "舞踏会" in result
    assert "前世の記憶" in result
    
    # バンフィーファンタジー（デフォルト）の第1話プロンプトテスト
    result = await agent.build_prompt(config, genre="banish_fantasy")
    
    # バンフィーファンタジー特有の指示が含まれていることを確認
    assert "理不尽な追放・虐げの提示" in result
    assert "絶叫または冷笑で引く" in result


@pytest.mark.asyncio
async def test_opening_booster_multigenre_cliffhanger_evaluation():
    """ジャンルごとにクリフハンガー評価が正しく走ることをテスト"""
    from src.services.auditors.cliffhanger_scorer import score_cliffhanger
    
    # モックのセットアップ
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "底辺配信者・同接1人の絶望 → 未知の隠し部屋/ユニークスキル覚醒 → 配信切り忘れで引く"
    
    agent = OpeningBoosterAgent(llm=mock_llm)
    
    # ダンジョンストリームジャンルのクリフハンガー評価テスト
    config = OpeningEpisodeConfig(ep_num=1, target_word_count=2000, inciting_incident="未知の隠し部屋発見", payoff_moment="スキル覚醒")
    result = await agent.generate_opening_episode(config, protagonist_name="テスト配信者", genre="dungeon_stream")
    
    # 結果が返ってくることを確認
    assert "ep_num" in result
    assert "content" in result
    assert "cliffhanger" in result
    assert result["ep_num"] == 1
    
    # クリフハンガー評価が行われていることを確認（実際のスコアはモックに依存）
    assert result["cliffhanger"] is not None