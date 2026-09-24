"""プラグインインターフェース定義 (Step 15).

コア機能とオプショナル拡張（マルチメディア、外部投稿等）の境界を確立する。
すべてのプラグインは :class:`PluginProtocol` に従う必要がある。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PluginProtocol(Protocol):
    """AutoNovel プラグインプロトコル.

    コア機能とオプショナル拡張の境界。実装は以下を満たすこと:

    - :meth:`initialize`: プラグインの初期化（リソース確保、設定読み込み等）。
      失敗時は例外を送出せず ``False`` を返し、プラグインを無効扱いにする。
    - :meth:`is_available`: 現在プラグインが利用可能か（外部サービス接続等）。
    - :meth:`shutdown`: プラグインの終了処理（リソース解放等）。
    """

    name: str

    def initialize(self) -> bool:
        """プラグインを初期化する。成功時 True、失敗時 False。"""
        ...

    def is_available(self) -> bool:
        """プラグインが現在利用可能かどうかを返す。"""
        ...

    def shutdown(self) -> None:
        """プラグインを終了し、リソースを解放する。"""
        ...


class BasePlugin:
    """PluginProtocol の標準実装基底クラス.

    プラグイン作成時のボイラープレートを削減する。サブクラスは
    :attr:`name` を上書きし、必要に応じて各メソッドをオーバーライドする。
    """

    name: str = "base"

    def __init__(self, **config: Any) -> None:
        self.config = config
        self._initialized = False

    def initialize(self) -> bool:
        """デフォルト実装: 常に成功。"""
        self._initialized = True
        return True

    def is_available(self) -> bool:
        """デフォルト実装: 初期化済みなら利用可能。"""
        return self._initialized

    def shutdown(self) -> None:
        """デフォルト実装: 初期化フラグを落とすのみ。"""
        self._initialized = False
