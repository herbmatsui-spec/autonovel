from typing import Any, Protocol


class IRepository(Protocol):
    """
    Repositoryインターフェースの基底定義。
    Phase 2で各リポジトリに必要なメソッドを統一的に定義する。
    """

    async def update_plot_blueprint(self, book_id: str, blueprint: Any) -> bool: ...

    async def create_book(self, book_data: Any) -> str: ...

    async def save_plot(self, plot_data: Any) -> bool: ...
