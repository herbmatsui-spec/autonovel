"""src.agent - DEPRECATED: Use src.agents instead.
Compatibility shim for legacy agent imports.
"""

import warnings
import sys

warnings.warn(
    "src.agent is deprecated; use src.agents instead",
    DeprecationWarning,
    stacklevel=2,
)

from src import agents

# 互換性のためのサブモジュールマッピング
from src.agents import hooks, memory, tools
sys.modules["src.agent.hooks"] = hooks
sys.modules["src.agent.memory"] = memory
sys.modules["src.agent.tools"] = tools

__all__ = ["agents", "hooks", "memory", "tools"]