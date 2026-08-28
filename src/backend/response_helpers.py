# Response helpers - to be implemented

from datetime import datetime, timezone
from typing import Any, Dict

def api_success(data: Any = None, message: str = "成功") -> Dict[str, Any]:
    """統一成功レスポンス"""
    return {
        "success": True,
        "message": message,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


from fastapi.responses import JSONResponse

def api_error(error_code: str, message: str, detail: Any = None, status_code: int = 400) -> JSONResponse:
    """統一エラーレスポンス"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error_code": error_code,
            "error_message": message,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

