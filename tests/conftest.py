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
    実際の SQLite データベースを用いた UnitOfWork を提供する。
    
    - 一時ファイルDBを作成し、最新スキーマを create_all で構築
    - コミットパスは ChromaDB へは同期せず Outbox テーブルに記録するため、
       ChromaDB が起動していなくても動作する
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    db_url = f"sqlite+aiosqlite:///{db_path}"
    
    # スキーマ構築（同期エンジン）
    sync_url = f"sqlite:///{db_path}"
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    
    manager = DatabaseManager(db_url)
    uow = UnitOfWork(db=manager)
    
    yield uow
    
    try:
        db_path.unlink()
    except OSError:
        pass


@pytest.fixture
def chroma_url():
    """CI環境の ChromaDB エンドポイント（docker-compose.ci.yml で 8000 番）"""
    import os
    
    return os.environ.get("CHROMA_URL", "http://localhost:8000")


@pytest.fixture
def mock_st_context():
    """Streamlit アプリ統合テスト用のコンテキストモック"""
    from tests.mocks.mock_streamlit import MockStreamlitContext
    
    return MockStreamlitContext()


@pytest.fixture
def mock_streamlit():
    """Streamlit モジュールをモックに置き換えるフィクスチャ"""
    from tests.mocks.mock_streamlit import patch_streamlit
    from tests.mocks.mock_streamlit import MockStreamlitContext
    
    def _mock_streamlit():
        context = MockStreamlitContext()
        patch_streamlit(context)
        return context
    
    return _mock_streamlit