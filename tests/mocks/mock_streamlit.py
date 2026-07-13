import sys
import types
from unittest.mock import MagicMock


class MockStreamlitSessionState(dict):
    """st.session_state をシミュレートする辞書クラス"""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'MockStreamlitSessionState' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(f"'MockStreamlitSessionState' object has no attribute '{name}'")

class MockStreamlitContext:
    """Streamlit コンテキストをエミュレートするコンテキストマネージャー"""
    def __init__(self):
        self.session_state = MockStreamlitSessionState()
        self.toast_calls = []
        self.error_calls = []
        self.write_calls = []
        self.metrics = {}
        self.navigation_run_called = False
        self.rerun_called = False
        self.api_key_input = "mock-api-key"
        self.app_mode_select = "easy"
        self.buttons_clicked = set()

    def set_api_key(self, api_key: str):
        self.api_key_input = api_key

    def set_app_mode(self, mode: str):
        self.app_mode_select = mode

    def click_button(self, label: str):
        self.buttons_clicked.add(label)

class MockStreamlitModule(types.ModuleType):
    """streamlitモジュールの振る舞いをするモックモジュール"""
    def __init__(self, context: MockStreamlitContext):
        super().__init__("streamlit")
        self.__path__ = []
        self.context = context

        # Define streamlit.errors submodule
        errors_mod = types.ModuleType("streamlit.errors")
        errors_mod.StreamlitAPIException = Exception
        self.errors = errors_mod
        sys.modules["streamlit.errors"] = errors_mod

        # Define streamlit.runtime and submodules
        runtime_mod = types.ModuleType("streamlit.runtime")
        runtime_mod.__path__ = []
        self.runtime = runtime_mod
        sys.modules["streamlit.runtime"] = runtime_mod

        scriptrunner_mod = types.ModuleType("streamlit.runtime.scriptrunner")
        scriptrunner_mod.get_script_run_ctx = MagicMock(return_value=None)
        self.runtime.scriptrunner = scriptrunner_mod
        sys.modules["streamlit.runtime.scriptrunner"] = scriptrunner_mod


    @property
    def session_state(self):
        return self.context.session_state

    def set_page_config(self, *args, **kwargs):
        pass

    def toast(self, message, icon=None):
        self.context.toast_calls.append((message, icon))

    def error(self, message):
        self.context.error_calls.append(message)

    def write(self, message):
        self.context.write_calls.append(message)

    def markdown(self, body, unsafe_allow_html=False):
        pass

    def title(self, body, anchor=None, help=None):
        pass

    def header(self, body, anchor=None, help=None):
        pass

    def subheader(self, body, anchor=None, help=None):
        pass

    def text(self, body):
        pass

    def code(self, body, language="python"):
        pass

    def json(self, body):
        pass

    def success(self, body, icon=None):
        pass

    def info(self, body, icon=None):
        pass

    def warning(self, body, icon=None):
        pass

    def divider(self):
        pass

    def metric(self, label, value):
        self.context.metrics[label] = value

    def columns(self, spec):
        return [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]

    class SidebarContext:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    @property
    def sidebar(self):
        return self.SidebarContext()

    def button(self, label, type=None, **kwargs):
        return label in self.context.buttons_clicked

    class SpinnerContext:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def spinner(self, text):
        return self.SpinnerContext()

    def rerun(self):
        self.context.rerun_called = True
        pass

    def navigation(self, pages):
        class MockNavigation:
            def __init__(self, ctx):
                self.ctx = ctx
            def run(self):
                self.ctx.navigation_run_called = True
        return MockNavigation(self.context)

    class Page:
        def __init__(self, page, title=None, icon=None, url_path=None, default=False):
            self.page = page
            self.title = title
            self.icon = icon
            self.url_path = url_path
            self.default = default

    def fragment(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        def decorator(func):
            return func
        return decorator

def patch_streamlit(context: MockStreamlitContext):
    """sys.modules['streamlit'] をモックに置き換える"""
    mock_st = MockStreamlitModule(context)
    sys.modules['streamlit'] = mock_st
    return mock_st
