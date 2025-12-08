"""
API Service - Main entrypoint
Handles payment requests and communicates with Payments service.
"""

import os
import redis
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from services.api.middleware.rate_limit import RateLimitMiddleware
import httpx
from prometheus_client import Counter, make_asgi_app

app = FastAPI(title="Resilience Lab - API Service")

PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://localhost:8001")

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    redis_client=redis_client,
    max_requests=60,
    window_seconds=60,  # per minute
    tenant_header="X-Tenant",
)

# Metrics
rl_allowed = Counter("rl_allowed_total", "Total allowed requests", ["tenant"])
rl_denied = Counter("rl_denied_total", "Total denied requests", ["tenant"])

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


class PaymentRequest(BaseModel):
    amount: float
    currency: str = "USD"
    tenant_id: str = "default"


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    amount: float
    currency: str


@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for K8s probes."""
    return {"status": "healthy", "service": "api"}


@app.post("/pay", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(payment: PaymentRequest) -> Dict[str, Any]:
    """
    Create a payment by calling the Payments service.
    This is the main integration point between API and Payments.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{PAYMENTS_URL}/process",
                json={
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "tenant_id": payment.tenant_id,
                },
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Payments service timeout",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Payments service error: {exc}",
        )


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "service": "resilience-lab-api",
        "version": "0.0.1",
        "endpoints": ["/healthz", "/pay"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
