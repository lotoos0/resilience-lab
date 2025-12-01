"""
Rate limiting middleware using Redis.
Enforces per-tenant request limits with sliding window
"""

import time
import uuid
import json
from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis import Redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit middleware using Redis sliding window.

    Enforces per-tenant limits based on X-Tenant header.
    """

    def __init__(
        self,
        app,
        redis_client: Redis,
        max_requests: int = 60,
        window_seconds: int = 60,
        tenant_header: str = "X-Tenant",
    ):
        super().__init__(app)
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.tenant_header = tenant_header

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting."""

        # Get tenant from header (default: 'default')
        tenant_id = request.headers.get(self.tenant_header, "default")

        # Check rate limit
        if not await self._check_rate_limit(tenant_id):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded for tenant {tenant_id}",
                    "limit": f"{self.max_requests} requests per {self.window_seconds}s",
                    "tenant": tenant_id,
                },
            )

        # Process request
        response = await call_next(request)
        return response

    async def _check_rate_limit(self, tenant_id: str) -> bool:
        """
        Check if tenant is within rate limit using sliding window.

        Returns:
            True if request allowed, False if rate limit exceeded
        """
        key = f"rate_limit:{tenant_id}"
        current_time = int(time.time())
        window_start = current_time - self.window_seconds

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries outside window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        pipe.zcard(key)

        # Add current request with unique ID
        request_id = str(uuid.uuid4())
        pipe.zadd(key, {request_id: current_time})

        # Set expiration
        pipe.expire(key, self.window_seconds)

        # Execute pipeline
        results = pipe.execute()
        request_count = results[1]  # zcard result

        # Check if under limit
        return request_count < self.max_requests
