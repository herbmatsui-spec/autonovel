from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from jinja2 import Environment

from prompts.registry import PromptRegistry
from prompts.schemas import PromptContext

logger = logging.getLogger(__name__)


class BasePromptBuilder(ABC):
    """プロンプトビルダーの基底抽象クラス。"""

    def __init__(self, registry: PromptRegistry, jinja_env: Optional[Environment] = None):
        self.registry = registry
        self.jinja_env = jinja_env or registry.jinja_env

    @abstractmethod
    async def render(self, context: PromptContext, book_id: Optional[int] = None) -> str:
        """コンテキストを元にプロンプトをレンダリングする。"""
