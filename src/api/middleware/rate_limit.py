import time
from typing import Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.clients = {}  # In production, use Redis or similar

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old entries (simple cleanup, not production ready)
        self.clients = {
            ip: data for ip, data in self.clients.items()
            if current_time - data["first_request_time"] < self.window_size
        }
        
        if client_ip not in self.clients:
            # First request from this IP
            self.clients[client_ip] = {
                "first_request_time": current_time,
                "request_count": 1,
            }
        else:
            data = self.clients[client_ip]
            if current_time - data["first_request_time"] > self.window_size:
                # Reset the window
                data["first_request_time"] = current_time
                data["request_count"] = 1
            else:
                data["request_count"] += 1
                if data["request_count"] > self.requests_per_minute:
                    raise HTTPException(
                        status_code=429,
                        detail="Too Many Requests",
                    )
        
        response = await call_next(request)
        return response