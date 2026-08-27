"""tests/unit/test_episode_writer_single_pass.py
EpisodeWriter のシングルパス生成および官能プロンプト結合・後処理適用の単体テスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.writing.episode_writer import EpisodeWriter


@pytest.mark.asyncio
async def test_episode_writer_single_pass_erotic_mode():
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "二人は温もりを確かめ合い、静かに息を整えた。セックスのような激しさではなく、深い余韻があった。"

    mock_context_builder = MagicMock()

    writer = EpisodeWriter(llm=mock_llm, context_builder=mock_context_builder)

    # PromptManager のモックを注入
    mock_pm = AsyncMock()
    mock_pm.build_final_writing_prompt.return_value = "【基本執筆プロンプト】"
    writer.prompt_manager = mock_pm

    context = {
        "plot": {"detailed_blueprint": "第1話のプロット"},
        "script": "台本テキスト",
        "target_word_count": 1500,
        "erotic_intensity": 2,
        "nsfw_enabled": True,
        "ep_num": 1,
    }

    result = await writer.write(book_id=1, ep_num=1, context=context)

    # 1. LLM呼び出しは1回のみ（シングルパス）であることを検証
    assert mock_llm.generate_text.call_count == 1

    # 2. generate_text に nsfw_mode=True が渡されていることを検証
    _, kwargs = mock_llm.generate_text.call_args
    assert kwargs.get("nsfw_mode") is True
    assert kwargs.get("purpose") == "writing"

    # 3. プロンプトに官能セクションが含まれていることを検証
    prompt_arg = kwargs.get("prompt")
    assert "【基本執筆プロンプト】" in prompt_arg
    assert "官能描写セーフティ・マニフェスト" in prompt_arg

    # 4. 後処理でメタファーフィルタが適用されていること（直接的な単語の置換）を検証
    assert "セックス" not in result
    assert "二人の夜" in result or "温もり" in result


@pytest.mark.asyncio
async def test_episode_writer_single_pass_normal_mode():
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "勇者は剣を構え、魔王に立ち向かった。"

    mock_context_builder = MagicMock()

    writer = EpisodeWriter(llm=mock_llm, context_builder=mock_context_builder)

    mock_pm = AsyncMock()
    mock_pm.build_final_writing_prompt.return_value = "【通常執筆プロンプト】"
    writer.prompt_manager = mock_pm

    context = {
        "plot": {"detailed_blueprint": "第1話のプロット"},
        "script": "台本テキスト",
        "target_word_count": 1500,
        "erotic_intensity": 0,
        "nsfw_enabled": False,
        "ep_num": 1,
    }

    result = await writer.write(book_id=1, ep_num=1, context=context)

    assert mock_llm.generate_text.call_count == 1
    _, kwargs = mock_llm.generate_text.call_args
    assert kwargs.get("nsfw_mode") is False
    prompt_arg = kwargs.get("prompt")
    assert "官能描写セーフティ・マニフェスト" not in prompt_arg
    assert result == "勇者は剣を構え、魔王に立ち向かった。"
