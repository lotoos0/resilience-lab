"""
API Service - Main entrypoint
Handles payment requests and communicates with Payments service.
"""

import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import httpx

app = FastAPI(title="Resilience Lab - API Service")

PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://localhost:8001")


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
