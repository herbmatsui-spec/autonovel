import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.planning import PlanningAgent
from src.models.beat_sheet import EpisodeBeat


@pytest.mark.asyncio
async def test_generate_commercial_beat_sheet():
    # モックのセットアップ
    mock_llm = AsyncMock()
    mock_prompt_manager = AsyncMock()

    # LLM.generate_json のモック返却値（CSV形式のテキスト）
    csv_lines = ["話数,フェーズ,ミッション,テンション目標,ビジュアルシーンフォーカス"]
    for i in range(1, 41):
        csv_lines.append(f"{i},フェーズ{i},ミッション{i},0.5,ビジュアル{i}")
    csv_text = "\n".join(csv_lines)

    mock_llm.generate_json.return_value = {
        "success": True,
        "data": csv_text,
    }

    # プロンプトマネージャのrender_asyncモック（実際に呼ばれるが、ここでは何もしない）
    mock_prompt_manager.render_async.return_value = "dummy prompt"

    agent = PlanningAgent(llm=mock_llm, prompt_manager=mock_prompt_manager)

    beats = await agent.generate_commercial_beat_sheet(
        title="テストタイトル",
        synopsis="テストあらすじ",
    )

    # アサーション
    assert len(beats) == 40
    assert all(isinstance(b, EpisodeBeat) for b in beats)
    assert beats[0].ep_num == 1
    assert beats[0].phase == "フェーズ1"
    assert beats[0].mission == "ミッション1"
    assert beats[0].tension_target == 0.5
    assert beats[0].visual_scene_focus == "ビジュアル1"

    # LLM.generate_json が正しい目的で呼ばれたことを確認
    mock_llm.generate_json.assert_awaited_once()
    args, kwargs = mock_llm.generate_json.call_args
    assert kwargs.get("purpose") == "planning"
    # プロンプトマネージャのrender_asyncが呼ばれたことを確認
    mock_prompt_manager.render_async.assert_awaited_once()