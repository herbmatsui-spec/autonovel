from fastapi import status


class AutoNovelException(Exception):
    """AutoNovel アプリケーションの基底例外クラス。

    Attributes:
        status_code (int): HTTP ステータスコード
        detail (str): エラー詳細メッセージ
    """

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "Internal server error",
    ):
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)

class NotFoundException(AutoNovelException):
    """リソースが見つからない場合の例外。"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ValidationException(AutoNovelException):
    """バリデーションエラーが発生した場合の例外。"""
    def __init__(self, detail: str = "Invalid input data"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class ServiceException(AutoNovelException):
    """サービス層でのビジネスロジックエラー。"""
    def __init__(self, detail: str = "Service processing error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
