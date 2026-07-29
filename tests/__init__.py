"""AutoNovel テストパッケージのルート。

pytest の asyncio_mode=auto を pyproject.toml で指定済みのため、
本パッケージは明示的な import を最小限に留める。conftest.py が
sys.path 修正と一時 DB フィクスチャを提供する。
"""
