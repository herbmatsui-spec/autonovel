"""下位互換性維持のためのシム。実体は src.services.audit.adapter に移動しました。"""
import warnings

warnings.warn(
    "src.services.audit_adapter is deprecated; use src.services.audit instead",
    DeprecationWarning,
    stacklevel=2,
)

from src.services.audit.adapter import AuditAdapter, create_audit_adapter  # noqa: F401

__all__ = ["AuditAdapter", "create_audit_adapter"]