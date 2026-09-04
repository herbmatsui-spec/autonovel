"""テスト用のモック LLM アダプタ。

このモックは、テストごとにレスポンスをカスタマイズできるように設計されています。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any


class LLMMocker:
    """LLM モックの振る舞いを設定するためのクラス。"""

    def __init__(self) -> None:
        self._responses: list[str] = []
        self._response_iter: int = 0
        self._exceptions: list[Exception] = []
        self._exception_iter: int = 0

    def set_responses(self, *responses: str) -> None:
        """生成するレスポンスのシーケンスを設定する。"""
        self._responses = list(responses)
        self._response_iter = 0

    def add_exception(self, *exceptions: Exception) -> None:
        """発生させる例外のシーケンスを設定する。"""
        self._exceptions = list(exceptions)
        self._exception_iter = 0

    def get_next_response(self) -> str:
        """次のレスポンスを取得する。"""
        if self._exception_iter < len(self._exceptions):
            raise self._exceptions[self._exception_iter]
            self._exception_iter += 1
        if self._response_iter < len(self._responses):
            response = self._responses[self._response_iter]
            self._response_iter += 1
            return response
        return "Mock response"

    def reset(self) -> None:
        """モックの状態をリセットする。"""
        self._responses = []
        self._response_iter = 0
        self._exceptions = []
        self._exception_iter = 0


class MockLLMAdapter:
    """テスト用モック LLM アダプタ。"""

    def __init__(self, mocker: LLMMocker | None = None) -> None:
        """モックアダプターを初期化する。"""
        self._mocker = mocker or LLMMocker()

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """テキストを一括生成する（モック実装）。"""
        return self._mocker.get_next_response()

    async def stream_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """テキストをストリーミング生成する（モック実装）。"""
        response = self._mocker.get_next_response()
        for chunk in response.split():
            yield chunk + " "
            await asyncio.sleep(0)

    def cancel(self) -> None:
        """進行中のストリームをキャンセルするフック。"""
        pass

    @property
    def mocker(self) -> LLMMocker:
        """内部の LLMMocker を取得する。"""
        return self._mocker