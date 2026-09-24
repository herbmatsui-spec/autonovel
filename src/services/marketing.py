"""下位互換性維持のためのシム。実体は src.services.marketing に移動しました。"""
import warnings

warnings.warn(
    "src.services.marketing (file) is deprecated; use src.services.marketing (package) instead",
    DeprecationWarning,
    stacklevel=2,
)

from src.services.marketing import (  # noqa: F401
    MarketingAgent,
    MarketingService,
    DEFAULT_FALLBACK,
    score_title_ctr,
    score_catchphrase_ctr,
    extract_syntax_features,
)

__all__ = [
    "MarketingAgent",
    "MarketingService",
    "DEFAULT_FALLBACK",
    "score_title_ctr",
    "score_catchphrase_ctr",
    "extract_syntax_features",
]
