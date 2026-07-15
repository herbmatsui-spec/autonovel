# デフォルトモデルマッピング（必要に応じて追加）
_DEFAULTS = {
    "planning": "gemini-3.1-flash-lite",
    "plot_expansion": "gemma-4-31b-it",
    "writing": "gemma-4-31b-it",
    "climax": "gemma-4-31b-it",
    "fallback": "gemma-4-31b-it",
    "ultra_stable": "gemma-4-31b-it",
    "audit": "gemini-3.1-flash-lite",
    "marketing": "gemini-3.1-flash-lite",
}

# select_model() で「用途」として解釈するキー群。
# これ以外の文字列はリテラルのモデルIDとして扱う。
_PURPOSES = set(_DEFAULTS.keys())

# OpenAI互換（GPT, Claude-via-OpenRouter, Llama, Mistral, Qwen,
# DeepSeek, Command, Gemini-via-OpenRouter 等）とみなすプレフィックス/キーワード。
# OpenRouter のモデルIDは "anthropic/claude-3.5-sonnet" のように "/" を含む。
_OPENAI_COMPAT_HINTS = (
    "gpt", "claude", "llama", "mistral", "qwen", "deepseek",
    "command", "anthropic", "openrouter", "sonar", "glm", "yi-",
    "phi", "cohere", "meta/", "mistralai/", "google/", "openai/",
    "anthropic/", "deepseek/", "qwen/",
)


def is_openai_compatible(model_name: str) -> bool:
    """モデル名がOpenAI互換API（OpenRouter等）経由で呼び出すべきかを判定する。"""
    if not model_name:
        return False
    # OpenRouter 等は "org/model" 形式のモデルIDを使う
    if "/" in model_name:
        return True
    lowered = model_name.lower()
    return any(hint in lowered for hint in _OPENAI_COMPAT_HINTS)


def select_model(purpose: str = "writing") -> str:
    """目的に応じたモデル名を返す。

    環境変数や `config.streamlit_adapter` の上書き設定があればそちらを優先。
    既知の「用途」でなければ、渡された文字列をそのままモデルIDとして返す。
    """
    # 用途でない（リテラルのモデルID等）場合はそのまま返す
    if purpose not in _PURPOSES:
        return purpose

    # 設定から取得を試みる (SSOT: GlobalConfigModel / settings.toml)
    key = f"model_{purpose}"
    try:
        from config.project_context import get_config
        value = getattr(get_config(), key, None)
        if value:
            return str(value)
    except Exception:
        pass
    return _DEFAULTS.get(purpose, "gemini-3.1-flash-lite")


def resolve_model(value: str) -> str:
    """LLM呼び出し時に渡された値（用途 or モデルID）を実際のモデル名に解決する。

    - 既知の用途 ("writing" 等) なら select_model() で設定値を解決
    - それ以外（"gemini-2.0-flash", "anthropic/claude-3.5-sonnet" 等）はそのまま返す
    """
    if value in _PURPOSES:
        return select_model(value)
    return value
