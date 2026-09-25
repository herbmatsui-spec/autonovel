"""Audit services package.

監査関連機能の統合:
- AuditAggregatorService: 公開ファサード（8スペシャリスト監査の集約）
- AuditService: 監査サービス（スクリーン・能力チェック・DeAI監査）
- AuditAdapter: 監査エンジン共通アダプタ
"""
from src.services.audit.aggregator import (
    AuditAggregator,
    BookScoreResult,
    SPECIALIST_NAMES,
)
from src.services.audit.service import AuditService
from src.services.audit.adapter import AuditAdapter, create_audit_adapter
from src.services.audit.fast_screener import FastScreener
from src.services.audit.targeted_diagnostic import TargetedDiagnostic

# 公開ファサード
AuditAggregatorService = AuditAggregator

__all__ = [
    "AuditAggregatorService",
    "AuditAggregator",
    "BookScoreResult",
    "SPECIALIST_NAMES",
    "AuditService",
    "AuditAdapter",
    "create_audit_adapter",
    "FastScreener",
    "TargetedDiagnostic",
]