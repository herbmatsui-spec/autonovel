"""グローバル例外ハンドラ (RFC 7807 準拠)。"""
from fastapi import Request, HTTPException, status, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.backend.schemas.problem_details import ProblemDetails


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException を RFC 7807 形式に変換"""
    problem = ProblemDetails(
        type=f"https://autonovel.local/errors/http-{exc.status_code}",
        title=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic バリデーションエラーを RFC 7807 形式に変換"""
    invalid_params = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        invalid_params.append({
            "name": loc,
            "reason": err.get("msg", "Invalid value"),
        })

    problem = ProblemDetails(
        type="https://autonovel.local/errors/validation-error",
        title="リクエストパラメータの検証に失敗しました",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="送信されたデータに形式または値の不正があります",
        instance=request.url.path,
        invalid_params=invalid_params,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )
