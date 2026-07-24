from __future__ import annotations

from typing import Any, Dict, Generic, Optional, Protocol, TypedDict, TypeVar

T = TypeVar("T")


class UIComponent(Protocol):
    """
    すべてのUIコンポーネントが実装すべき基本インターフェース。
    View層のコンポーネントを抽象化し、テストや差し替えを容易にする。
    """

    def render(self, state: Dict[str, Any], **kwargs: Any) -> Any: ...


class UIResponse(Generic[T]):
    """
    コントローラーからUIへ返却される標準的なレスポンス形式。
    """

    status: str  # "success", "error", "started", "completed"
    data: Optional[T] = None
    message: Optional[str] = None
    error_code: Optional[str] = None


class UIStateView(Protocol):
    """
    UIが状態にアクセスするための読み取り専用インターフェース。
    直接 st.session_state に触れるのではなく、UIStateStore を介してアクセスすること。
    """

    def get(self, key: str, default: Any = None) -> Any: ...
    def get_all(self) -> Dict[str, Any]: ...


class RenderContext(TypedDict):
    """
    レンダリング時にコンポーネントに渡される共通コンテキスト。
    """

    state: Dict[str, Any]
    engine: Any
    book_id: Optional[int]
    user_id: Optional[str]


class StreamDisplayInterface(Protocol):
    """
    ストリーミング表示（プログレスバー、リアルタイムログ、逐次テキスト生成）の抽象インターフェース。
    UIフレームワーク（Streamlit等）に依存しない表示制御を可能にする。
    """

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """進捗率とメッセージを更新する"""
        ...

    def append_log(self, message: str) -> None:
        """ログを末尾に追加する"""
        ...

    def update_text(self, text: str, finalize: bool = False) -> None:
        """逐次生成されるテキストを更新する"""
        ...

    def set_error(self, error_message: str, trace_id: Optional[str] = None) -> None:
        """エラー状態を表示する"""
        ...

    def set_complete(self, result_data: Any = None, message: str = "") -> None:
        """完了状態を表示し、結果データを提示する"""
        ...
