"""
src/prototype/llm_adapter.py - novel_50ep 用 LLM ゲートウェイアダプタ
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Dict, Optional


class GatewayLLMGenerator:
    """本番 LLMGateway を呼び出し、novel_50ep の Generator シグネチャと互換性を保つアダプタ"""

    def __init__(self, llm_gateway: Optional[Any] = None, world_data: Optional[Dict[str, Any]] = None):
        self.llm_gateway = llm_gateway
        self.world = world_data or {}

    async def agenerate(
        self,
        prompt: str,
        target_chars: int = 0,
        part_id: int = 1,
        ep: int = 1,
        cliff: str = "",
        **kw: Any,
    ) -> str:
        """非同期でテキスト生成を行う"""
        if self.llm_gateway is not None:
            if hasattr(self.llm_gateway, "generate_text"):
                res = await self.llm_gateway.generate_text(purpose_or_request="writing", prompt=prompt, **kw)
                if hasattr(res, "story_content"):
                    return res.story_content
                if isinstance(res, str):
                    return res
                return str(res)
            elif callable(self.llm_gateway):
                res = self.llm_gateway(prompt, target_chars=target_chars, part_id=part_id, ep=ep, cliff=cliff, **kw)
                if asyncio.iscoroutine(res):
                    res = await res
                return str(res)

        # デフォルトで src.core.llm_gateway の利用を試みる
        try:
            from src.core.llm_gateway import LLMGateway
            gw = LLMGateway()
            res = await gw.generate_text(purpose_or_request="writing", prompt=prompt, **kw)
            return res.story_content if hasattr(res, "story_content") else str(res)
        except Exception:
            # フォールバック: MockLLMGenerator
            try:
                from novel_50ep.generator import MockLLMGenerator
                mock = MockLLMGenerator(self.world)
                return mock.generate(prompt, target_chars, part_id, ep, cliff)
            except Exception:
                return f"第{ep}話 パート{part_id}: {prompt[:30]}..."

    def generate(
        self,
        prompt: str,
        target_chars: int = 0,
        part_id: int = 1,
        ep: int = 1,
        cliff: str = "",
        **kw: Any,
    ) -> str:
        """同期インターフェース（既存 novel_50ep との後方互換）"""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        lambda: asyncio.run(
                            self.agenerate(prompt, target_chars, part_id, ep, cliff, **kw)
                        )
                    )
                    return future.result()
            else:
                return asyncio.run(
                    self.agenerate(prompt, target_chars, part_id, ep, cliff, **kw)
                )
        except Exception:
            try:
                from novel_50ep.generator import MockLLMGenerator
                mock = MockLLMGenerator(self.world)
                return mock.generate(prompt, target_chars, part_id, ep, cliff)
            except Exception:
                return f"第{ep}話 パート{part_id}: {prompt[:30]}..."
