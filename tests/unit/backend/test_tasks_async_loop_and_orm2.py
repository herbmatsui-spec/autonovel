"""_run_async および SQLAlchemy 2.0 session.get の動作検証テスト"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from src.backend.tasks.generation_tasks import _run_async, _get_user_id_from_book_id


def test_run_async_properly_handles_coroutine():
    """_run_async がコルーチンを正しく実行して結果を返す"""

    async def sample_coro():
        await asyncio.sleep(0.01)
        return "async_result"

    result = _run_async(sample_coro())
    assert result == "async_result"


def test_run_async_handles_exception():
    """_run_async が例外を適切に伝播する"""

    async def failing_coro():
        await asyncio.sleep(0.01)
        raise ValueError("test error")

    with pytest.raises(ValueError, match="test error"):
        _run_async(failing_coro())


def test_run_async_handles_none_return():
    """None を返すコルーチンも正しく処理する"""

    async def none_coro():
        await asyncio.sleep(0.01)
        return None

    result = _run_async(none_coro())
    assert result is None


def test_run_async_multiple_awaits():
    """複数の await を含むコルーチンも正しく処理する"""

    async def multi_coro():
        await asyncio.sleep(0.005)
        intermediate = "step1"
        await asyncio.sleep(0.005)
        return intermediate + "_step2"

    result = _run_async(multi_coro())
    assert result == "step1_step2"


@patch("src.backend.tasks.generation_tasks.database.SessionLocal")
def test_get_user_id_from_book_id_success(mock_session_local):
    """書籍IDからユーザーIDを正常に取得できる"""
    # モックセッションと書籍オブジェクトの設定
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session

    mock_book = MagicMock()
    mock_book.user_id = 42
    mock_session.get.return_value = mock_book

    # 実行
    result = _get_user_id_from_book_id(123)

    # 検証
    assert result == 42
    mock_session_local.assert_called_once()
    # session.get はクラスとIDで呼ばれる（文字列ではなくクラスオブジェクト）
    mock_session.get.assert_called_once()
    call_args = mock_session.get.call_args
    assert call_args[0][1] == 123  # 第2引数が book_id
    mock_session.close.assert_called_once()


@patch("src.backend.tasks.generation_tasks.database.SessionLocal")
def test_get_user_id_from_book_id_not_found(mock_session_local):
    """存在しない書籍IDの場合 ValueError を送出する"""
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session
    mock_session.get.return_value = None

    with pytest.raises(ValueError, match="Book not found: 999"):
        _get_user_id_from_book_id(999)

    mock_session.close.assert_called_once()


@patch("src.backend.tasks.generation_tasks.database.SessionLocal")
def test_get_user_id_from_book_id_exception_cleanup(mock_session_local):
    """例外発生時もセッションがクローズされる"""
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session
    mock_session.get.side_effect = Exception("DB error")

    with pytest.raises(Exception, match="DB error"):
        _get_user_id_from_book_id(123)

    mock_session.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])