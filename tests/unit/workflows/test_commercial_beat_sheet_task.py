"""商用ビートシート生成が「タスク発行型」になったことの回帰テスト。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest

from src.backend.routers import commercial_planning


@pytest.mark.asyncio
async def test_generate_returns_task_id_instead_of_rows():
    """同期で40行を返さず、task_id だけを返すこと（イベントループのブロック防止）。"""
    user = SimpleNamespace(id=1, role="user")
    req = commercial_planning.BeatSheetGenerateRequest(title="T", synopsis="S", book_id=1)
    with patch("src.backend.tasks.execute_service_workflow") as mock_exec, \
         patch("src.backend.task_helpers.create_task", new_callable=AsyncMock):
        result = await commercial_planning.generate_beat_sheet(
            request=req,
            current_user=user,
        )
    assert "task_id" in result
    assert result["task_id"].startswith("commercial_beats_")
    mock_exec.assert_called_once()
