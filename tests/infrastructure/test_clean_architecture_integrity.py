"""
tests/infrastructure/test_clean_architecture_integrity.py
Part 5 (Step 16-18) リグレッション防止テスト:
二重化解消（src.agent -> src.agents）、レガシー database/core.py 撤廃後の
モジュールインポート健全性とクリーンアーキテクチャ整合性を検証。
"""

import warnings
import pytest


def test_src_agent_imports_resolve_to_agents():
    """src.agent からのインポートが DeprecationWarning を伴いながら安全に src.agents に解決されることを検証"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        import src.agent
        assert any(issubclass(item.category, DeprecationWarning) for item in w)
        assert hasattr(src.agent, "agents")


def test_no_broken_database_imports_across_project():
    """ルート直下の database.core が撤廃され、narrative_metrics_db が新基盤 Base を継承していることを検証"""
    # 旧 database.core は存在しないこと
    with pytest.raises(ModuleNotFoundError):
        import database.core  # noqa

    # narrative_metrics_db が正常に読み込めること
    from src.models.narrative_metrics_db import NarrativeMetric
    from src.infrastructure.database.models import Base
    assert issubclass(NarrativeMetric, Base)


def test_core_orm_models_load_cleanly():
    """主要ドメインモデルがクリーンに読み込めることを検証"""
    from src.backend.database.models import Book, Chapter, Character, Plot
    from src.infrastructure.database.models.task import Task
    assert Book.__tablename__ == "books"
    assert Chapter.__tablename__ == "chapters"
    assert Character.__tablename__ == "characters"
    assert Plot.__tablename__ == "plots"
    assert Task.__tablename__ == "tasks"
