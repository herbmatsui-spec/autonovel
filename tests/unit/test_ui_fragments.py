import inspect

# 依存関係をモック化してインポートエラーを防ぐ
import sys
from unittest.mock import MagicMock

import pytest

# streamlit のモック作成
mock_st = MagicMock()
mock_st.fragment = lambda x: x
sys.modules["streamlit"] = mock_st

# ターゲット関数のインポート

def test_fragments_decorators():
    """
    各関数に @st.fragment デコレータが適用されているかを確認する。
    """
    import streamlit_app.ui_tabs_writing as ui_writing
    source = inspect.getsource(ui_writing)

    # デコレータが存在することを確認
    assert "@st.fragment" in source, "@st.fragment decorator should be present in the source code"

    # 各関数の定義の前に @st.fragment が記述されているかを検証
    #- 空白を正規化（1つに）してチェック
    import re
    normalized_source = re.sub(r'\s+', ' ', source)

    assert "@st.fragment def render_plot_tab" in normalized_source, "render_plot_tab should have @st.fragment"
    assert "@st.fragment def render_episode_list" in normalized_source, "render_episode_list should have @st.fragment"
    assert "@st.fragment def render_import_tab" in normalized_source, "render_import_tab should have @st.fragment"

def test_render_writing_tab_calls_episode_list():
    """
    render_writing_tab が render_episode_list を呼び出していることを確認する。
    """
    import streamlit_app.ui_tabs_writing as ui_writing
    source = inspect.getsource(ui_writing.render_writing_tab)

    assert "render_episode_list(" in source, "render_writing_tab must call render_episode_list to ensure partial updates"

if __name__ == "__main__":
    pytest.main([__file__])
