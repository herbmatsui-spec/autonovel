"""NextBeatsService の単体テスト."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.models.editor import (
    BranchType,
    NextBeatsRequest,
)
from src.services.next_beats_service import NextBeatsService


@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock_result = MagicMock()
    mock_result.story_content = """
    ```json
    {
      "title": "逆転の魔導一閃",
      "summary": "アルトが古代の魔剣を解放し、敵の結界を打ち砕く",
      "content": "「これで終わりだ！」アルトの放った蒼き閃光が空間を裂き、立ちはだかる巨人を貫いた。",
      "hook_text": "しかし、砕け散る敵の破片から邪悪な笑い声が響く。"
    }
    ```
    """
    mock.generate_text = AsyncMock(return_value=mock_result)
    return mock


@pytest.mark.asyncio
async def test_generate_three_beats_success(mock_llm):
    """3バリエーション正常並列生成テスト"""
    service = NextBeatsService(llm_gateway=mock_llm)
    req = NextBeatsRequest(
        book_id=1,
        current_text="ダンジョンの奥底で、巨大なゴーレムが立ちふさがった。",
        genre="ハイファンタジー (R15)",
    )

    res = await service.generate_three_beats(req)

    assert len(res.beats) == 3
    assert res.beats[0].branch_type == BranchType.ROYAL
    assert res.beats[1].branch_type == BranchType.TWIST
    assert res.beats[2].branch_type == BranchType.PSYCHOLOGY
    assert res.beats[0].title == "逆転の魔導一閃"
    assert "これで終わりだ" in res.beats[0].content


@pytest.mark.asyncio
async def test_generate_three_beats_partial_failure():
    """一部のLLM呼び出し失敗時のフォールバックテスト"""
    mock_llm = MagicMock()
    # 1回目は成功、2回目は例外、3回目は成功
    succ_result = MagicMock()
    succ_result.story_content = '{"title": "成功カード", "summary": "概要", "content": "本文", "hook_text": "引き"}'

    mock_llm.generate_text = AsyncMock(
        side_effect=[succ_result, RuntimeError("LLM API Timeout"), succ_result]
    )

    service = NextBeatsService(llm_gateway=mock_llm)
    req = NextBeatsRequest(
        book_id=1,
        current_text="戦闘の最中……",
    )

    res = await service.generate_three_beats(req)

    assert len(res.beats) == 3
    assert res.beats[0].title == "成功カード"
    assert "エラーが発生しました" in res.beats[1].summary  # 失敗カードのフォールバック
    assert res.beats[2].title == "成功カード"
