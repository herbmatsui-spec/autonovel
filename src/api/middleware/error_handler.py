import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            # Log the exception
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            
            # Optionally, send to Sentry if available
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(exc)
            except ImportError:
                pass  # Sentry not available, ignore
            
            # Return a generic error message
            return JSONResponse(
                status_code=500,
                content={"message": "Internal Server Error"},
            )