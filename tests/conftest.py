"""
tests/conftest.py
pytest設定・共有fixtures
"""
import pytest
from unittest.mock import Mock
import sys, os
# Ensure project root is on PYTHONPATH for test imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.erotic_vocabulary import METAPHOR_BANK, ONOMATOPOEIA_BANK, PSYCHOLOGY_TEMPLATES


@pytest.fixture
def erotic_vocabulary():
    """エロティック語彙バンクを提供するフィクスチャ"""
    return {
        "metaphors": METAPHOR_BANK,
        "onomatopoeia": ONOMATOPOEIA_BANK,
        "psychology": PSYCHOLOGY_TEMPLATES,
    }


@pytest.fixture
def sample_erotic_text():
    """サンプルエロティックテキストを提供するフィクスチャ"""
    return """
    迸ｳ繧呈弌縺ｮ迸ｬ縺阪↓萓九∴繧九嘉   * 20  # ~400文字程度の段落
    蜍輔″邯壹￠繧九嘉 * 50 + "蜍輔″邯壹￠繧九。" * 3
    """.strip()


@pytest.fixture
def real_db_manager():
    """
    統合テスト用のデータベースマネージャー

    一時ファイルDBを作成し、最新スキーマを build して返す。
    各テストで独立したDBを使うため、並列実行/反復実行でも干渉しない。
    """
    import tempfile
    from pathlib import Path

    from sqlalchemy import create_engine

    from src.backend.database.core import DatabaseManager
    from src.backend.database.models import Base

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    db_url = f"sqlite+aiosqlite:///{db_path}"

    sync_url = f"sqlite:///{db_path}"
    sync_engine = create_engine(sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    db = DatabaseManager(db_url)
    yield db

    try:
        db_path.unlink()
    except OSError:
        pass


@pytest.fixture
def mock_llm():
    """LLM応答のモック（非同期 generate に対応した実クライアント互換オブジェクト）"""
    from tests.mocks.mock_llm import MockGeminiApiClient

    return MockGeminiApiClient()
