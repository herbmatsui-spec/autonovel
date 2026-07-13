"""
tests/conftest.py
pytest設定・共有fixtures
"""
import pytest
from unittest.mock import Mock

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

    get_db_manager() から実際の db_manager インスタンスを取得して返す。
    """
    from src.backend.database.core import get_db_manager
    db = get_db_manager()
    return db


@pytest.fixture
def mock_llm():
    """LLM応答のモック"""
    mock = Mock()
    mock.add_json_response = Mock()
    mock.add_text_response = Mock()
    mock.add_exception = Mock()
    return mock
