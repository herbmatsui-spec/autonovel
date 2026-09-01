"""
kernels/engines.py - 生成エンジンの基盤
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import KernelBase, KernelState


class EngineConfig(BaseModel):
    """エンジン設定"""

    model: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0)
    presence_penalty: float = Field(default=0.0)
    stop_sequences: List[str] = Field(default_factory=list)


class GenerationResult(BaseModel):
    """生成結果"""

    text: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GenerationEngine(KernelBase):
    """
    テキスト生成エンジン
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        super().__init__()
        self.config = config or EngineConfig()
        self._initialized = False

    async def initialize(self) -> bool:
        """エンジンを初期化"""
        # 実際の初期化処理（APIクライアントのセットアップ等）
        self._initialized = True
        self.set_state(KernelState.ACTIVE)
        return True

    async def generate(
        self, prompt: str, config: Optional[EngineConfig] = None, **kwargs
    ) -> GenerationResult:
        """テキストを生成"""
        if not self._initialized:
            await self.initialize()

        current_config = config or self.config

        # 実際のAPI呼び出し（テスト環境ではシミュレーション）
        result_text = f"[Generated text based on prompt: {prompt[:50]}...]"

        return GenerationResult(
            text=result_text,
            tokens_used=100,
            finish_reason="stop",
            metadata={"model": current_config.model},
        )

    async def execute(self, *args, **kwargs) -> Any:
        """エンジン実行"""
        prompt = kwargs.get("prompt", "")
        return await self.generate(prompt)


class LLMEngine(GenerationEngine):
    """
    LLMを使用した生成エンジン
    """

    def __init__(self, api_key: str, config: Optional[EngineConfig] = None):
        super().__init__(config)
        self.api_key = api_key
        self.base_url: Optional[str] = None

    async def set_base_url(self, url: str) -> None:
        """ベースURLを設定"""
        self.base_url = url

    async def execute(self, *args, **kwargs) -> Any:
        """LLMエンジン実行"""
        return await super().execute(*args, **kwargs)
