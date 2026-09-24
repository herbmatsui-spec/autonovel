"""src.agent - DEPRECATED: Use src.agents instead."""

import warnings
warnings.warn(
    "src.agent is deprecated; use src.agents instead",
    DeprecationWarning,
    stacklevel=2
)

from src.agents import *
from src.agents.tools import *
from src.agents.memory import *
from src.agents.hooks import *