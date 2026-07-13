from typing import Literal

# デフォルトモデルマッピング（必要に応じて追加）
_DEFAULTS = {
    "planning": "gemini-2.0-flash",
    "writing": "gemini-2.0-flash",
    "audit": "gemini-2.0-flash",
    "marketing": "gemini-2.0-flash",
}

def select_model(purpose: Literal["planning", "writing", "audit", "marketing"] = "writing") -> str:
    """目的に応じたモデル名を返す。
    環境変数や `config.streamlit_adapter` の上書き設定があればそちらを優先。
    """
    # 設定から取得を試みる
    try:
        from config.streamlit_adapter import StreamlitConfig
        cfg = StreamlitConfig()
        key = f"model_{purpose}"
        value = getattr(cfg, key, None)
        if value:
            return value
    except Exception:
        pass
    return _DEFAULTS.get(purpose, "gemini-2.0-flash")
