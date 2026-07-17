import inspect
import pytest

# 依存関係をモック化してインポートエラーを防ぐ
import sys
from unittest.mock import MagicMock

import pytest

# streamlit のモック作成
mock_st = MagicMock()
mock_st.fragment = lambda x: x
sys.modules["streamlit"] = mock_st

# ターゲット関数のインポート

def test_render_novel_production_tab_defined():
    """
    render_novel_production_tab が定義され、呼び出し可能であることを確認する。
    （ui_tabs_writing.py は複数の fragment 関数を単一の
    render_novel_production_tab に統合済み。旧テストが期待していた
    render_plot_tab / render_episode_list / render_import_tab /
    render_writing_tab は存在しない。）
    """
    import streamlit_app.ui_tabs_writing as ui_writing

    assert hasattr(ui_writing, "render_novel_production_tab"), (
        "render_novel_production_tab must be defined"
    )
    assert callable(ui_writing.render_novel_production_tab), (
        "render_novel_production_tab must be callable"
    )


def test_render_novel_production_tab_calls_commercial_api():
    """
    render_novel_production_tab が商用化パイプラインの API
    (/api/commercial/run) を呼び出すことを確認する。
    """
    import streamlit_app.ui_tabs_writing as ui_writing

    source = inspect.getsource(ui_writing.render_novel_production_tab)

    assert "/api/commercial/run" in source, (
        "render_novel_production_tab must call the commercial pipeline API"
    )


def test_render_novel_production_tab_calls_commercial_api():
    """
    render_novel_production_tab が商用化パイプラインの API
    (/api/commercial/run) を呼び出すことを確認する。
    """
    import streamlit_app.ui_tabs_writing as ui_writing

    source = inspect.getsource(ui_writing.render_novel_production_tab)

    assert "/api/commercial/run" in source, (
        "render_novel_production_tab must call the commercial pipeline API"
    )


def test_render_novel_production_tab_button_click_triggers_rerun():
    """
    Test that clicking the button in render_novel_production_tab triggers rerun.
    """
    import streamlit_app.ui_tabs_writing as ui_writing
    
    # Mock the click and rerun
    original_click = ui_writing.render_novel_production_tab.__globals__['st'].button
    original_rerun = ui_writing.render_novel_production_tab.__globals__['st'].rerun
    
    click_called = False
    rerun_called = False
    
    def mock_click(label):
        nonlocal click_called
        click_called = True
        return label in {"commercial_run"}
    
    def mock_rerun():
        nonlocal rerun_called
        rerun_called = True
    
    # Patch the methods
    ui_writing.render_novel_production_tab.__globals__['st'].button = mock_click
    ui_writing.render_novel_production_tab.__globals__['st'].rerun = mock_rerun
    
    # Call the function
    ui_writing.render_novel_production_tab()
    
    assert click_called, "Button click should have been called"
    assert rerun_called, "Rerun should have been triggered"