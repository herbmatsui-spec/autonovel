"""
パッケージインポート整合性と誤削除再発防止テスト (Step 2)
"""

import pytest


def test_database_types_import():
    """src.infrastructure.database.types から主要型が正常にインポートできること"""
    from src.infrastructure.database.types import (
        CompatibleJSON,
        CompatibleDateTime,
        CompatibleVector,
    )
    assert CompatibleJSON is not None
    assert CompatibleDateTime is not None
    assert CompatibleVector is not None


def test_backend_database_import():
    """src.backend.database から DB セッション取得関数がインポートできること"""
    from src.backend.database import get_async_db, get_db
    assert callable(get_async_db)
    assert callable(get_db)


def test_models_import():
    """src.models からモデルクラスがインポートできること"""
    from src.models import FullAutoWorkflowResult
    assert FullAutoWorkflowResult is not None


def test_domain_writing_import():
    """src.domain.writing からドメインサービスがインポートできること"""
    from src.domain.writing import WritingService
    assert WritingService is not None


def test_anti_ai_import():
    """src.services.anti_ai からアンチAI検出器がインポートできること"""
    from src.services.anti_ai import RuleBasedAntiAIDetector
    assert RuleBasedAntiAIDetector is not None
