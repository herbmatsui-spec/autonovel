from __future__ import annotations


class PromptError(Exception):
    """プロンプトシステムの基底例外クラス。"""

    def __init__(self, message: str, template_name: str | None = None, *args):
        super().__init__(message, *args)
        self.message = message
        self.template_name = template_name


class PromptTemplateNotFoundError(PromptError):
    """テンプレートファイルが見つからない場合の例外。"""

    def __init__(self, message: str, template_name: str | None = None):
        super().__init__(message, template_name)


class PromptRenderingError(PromptError):
    """Jinja2レンダリング失敗時の例外（変数不足等）。"""

    def __init__(self, message: str, template_name: str | None = None, missing_keys: list[str] | None = None):
        super().__init__(message, template_name)
        self.missing_keys = missing_keys or []


class PromptContextError(PromptError):
    """Pydanticバリデーション失敗等のコンテキスト不備。"""

    def __init__(self, message: str, template_name: str | None = None, invalid_fields: list[str] | None = None):
        super().__init__(message, template_name)
        self.invalid_fields = invalid_fields or []


class PromptRegistryError(PromptError):
    """レジストリ固有の失敗（キャッシュ破損等）の基底。"""

    def __init__(self, message: str, template_name: str | None = None):
        super().__init__(message, template_name)


class PromptCacheError(PromptRegistryError):
    """キャッシュ操作の失敗。"""

    def __init__(self, message: str, template_name: str | None = None):
        super().__init__(message, template_name)


class PromptDbError(PromptRegistryError):
    """DBからのプロンプト取得失敗。"""

    def __init__(self, message: str, template_name: str | None = None, book_id: int | None = None):
        super().__init__(message, template_name)
        self.book_id = book_id


class PromptBuilderError(PromptError):
    """Builder層でのロジック失敗。"""

    def __init__(self, message: str, template_name: str | None = None, builder_name: str | None = None):
        super().__init__(message, template_name)
        self.builder_name = builder_name
