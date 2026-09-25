"""下位互換性維持のためのシム。実体は src.services.audit.service に移動しました。"""
import importlib
import sys
import types
import warnings

warnings.warn(
    "src.services.audit_service is deprecated; use src.services.audit instead",
    DeprecationWarning,
    stacklevel=2,
)

_TARGET_MODULE = "src.services.audit.service"

from src.services.audit.service import (  # noqa: F401
    AuditService,
    FastPlotScreener,
    AbilityConsistencyChecker,
    DeAIAuditor,
    MAX_CONSECUTIVE_PEAK_EPISODES,
)

__all__ = [
    "AuditService",
    "FastPlotScreener",
    "AbilityConsistencyChecker",
    "DeAIAuditor",
    "MAX_CONSECUTIVE_PEAK_EPISODES",
]


class _ShimModule(types.ModuleType):
    def __getattr__(self, name: str):
        mod = importlib.import_module(_TARGET_MODULE)
        val = getattr(mod, name)
        super().__setattr__(name, val)
        return val

    def __setattr__(self, name: str, value):
        if name.startswith("__") or name in ("_actual_mod",):
            super().__setattr__(name, value)
            return
        try:
            mod = importlib.import_module(_TARGET_MODULE)
            setattr(mod, name, value)
        except Exception:
            pass
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _ShimModule