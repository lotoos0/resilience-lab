"""
Rate limiting middleware using Redis.
Enforces per-tenant request limits with sliding window
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis import Redis
from prometheus_client import Counter

logger = logging.getLogger(__name__)
# Metrics
rl_allowed = Counter("rl_allowed_total", "Total allowed requests", ["tenant"])
rl_denied = Counter("rl_denied_total", "Total denied requests", ["tenant"])


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
        allowed, current_count = await self._check_rate_limit(tenant_id)

        # Log rate limit check
        logger.info(
            "Rate limit check",
            extra={
                "tenant": tenant_id,
                "path": request.url.path,
                "current_count": current_count,
                "limit": self.max_requests,
                "status": "allowed" if allowed else "denied",
            },
        )

        if not allowed:
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

    async def _check_rate_limit(self, tenant_id: str) -> tuple[bool, int]:
        """
        Check if tenant is within rate limit using sliding window.

        Returns:
            Tuple of (allowed: bool, current_count: int)
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

        # Check if under limit and track metrics
        if request_count < self.max_requests:
            rl_allowed.labels(tenant=tenant_id).inc()
            return True, request_count
        else:
            rl_denied.labels(tenant=tenant_id).inc()
            return False, request_count
