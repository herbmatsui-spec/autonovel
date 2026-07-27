import os
import sys
import tempfile
from pathlib import Path
import pytest
from typing import AsyncGenerator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
async def real_db_manager() -> AsyncGenerator[Path, None]:
    """
    実際の SQLite 一時データベース管理器を提供する。
    統合テスト・ワークフローテストに使用される。
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)

    yield db_path

    try:
        if db_path.exists():
            db_path.unlink()
    except OSError:
        pass
