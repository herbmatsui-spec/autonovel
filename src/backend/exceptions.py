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
        super().__init__(status_code=422, detail=detail)

class ServiceException(AutoNovelException):
    """サービス層でのビジネスロジックエラー。"""
    def __init__(self, detail: str = "Service processing error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class MultimediaDisabledError(AutoNovelException):
    """Multimedia 機能が無効な場合に発生する例外。"""
    def __init__(self, detail: str = "Multimedia features are disabled"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
