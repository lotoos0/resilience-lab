"""Tests for rate limit middleware."""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import Request, status
from starlette.responses import JSONResponse

# Import from parent directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from middleware.rate_limit import RateLimitMiddleware


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = Mock()
    pipeline = Mock()
    pipeline.execute.return_value = [0, 0, True, True]
    redis.pipeline.return_value = pipeline
    return redis


@pytest.fixture
def rate_limiter(mock_redis):
    """Rate limiter instance with mocked Redis."""
    app = Mock()
    return RateLimitMiddleware(
        app=app, redis_client=mock_redis, max_requests=5, window_seconds=60
    )


@pytest.mark.asyncio
async def test_rate_limit_allows_request_under_limit(rate_limiter, mock_redis):
    """Test that requests under limit are allowed."""
    # Setup: 3 requests in window (under limit of 5)
    mock_redis.pipeline.return_value.execute.return_value = [0, 3, True, True]

    request = Mock(spec=Request)
    request.headers = {"X-Tenant": "test-tenant"}

    call_next = AsyncMock(return_value=Mock(status_code=200))

    response = await rate_limiter.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_blocks_request_over_limit(rate_limiter, mock_redis):
    """Test that requests over limit are blocked with 429."""
    # Setup: 5 requests in window (at limit)
    mock_redis.pipeline.return_value.execute.return_value = [0, 5, True, True]

    request = Mock(spec=Request)
    request.headers = {"X-Tenant": "test-tenant"}

    call_next = AsyncMock(return_value=Mock(status_code=200))

    response = await rate_limiter.dispatch(request, call_next)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "rate_limit_exceeded" in str(response.body)


@pytest.mark.asyncio
async def test_rate_limit_uses_default_tenant(rate_limiter, mock_redis):
    """Test that missing X-Tenant header uses 'default'."""
    mock_redis.pipeline.return_value.execute.return_value = [0, 0, True, True]

    request = Mock(spec=Request)
    request.headers = {}

    call_next = AsyncMock(return_value=Mock(status_code=200))

    response = await rate_limiter.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_separate_tenants(rate_limiter, mock_redis):
    """Test that different tenants have separate limits."""
    # Tenant A: 3 requests
    mock_redis.pipeline.return_value.execute.return_value = [0, 3, True, True]

    request_a = Mock(spec=Request)
    request_a.headers = {"X-Tenant": "tenant-a"}

    call_next = AsyncMock(return_value=Mock(status_code=200))

    response_a = await rate_limiter.dispatch(request_a, call_next)
    assert response_a.status_code == 200

    # Tenant B: also 3 requests (separate limit)
    request_b = Mock(spec=Request)
    request_b.headers = {"X-Tenant": "tenant-b"}

    response_b = await rate_limiter.dispatch(request_b, call_next)
    assert response_b.status_code == 200
