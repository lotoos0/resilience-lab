"""
Payments Service - Main entrypoint
Handles payment processing and persistence.
"""

import uuid
from typing import Dict, Any
from fastapi import FastAPI, status
from pydantic import BaseModel, Field

app = FastAPI(title="Resilience Lab - Payments Service")

# In-memory storage for demo (will be replaced with PG in future iterations)
payments_store: Dict[str, Dict[str, Any]] = {}


class PaymentProcessRequest(BaseModel):
    amount: float = Field(gt=0, description="Payment amount must be greater than 0")
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$", description="ISO 4217 currency code")
    tenant_id: str = "default"


class PaymentProcessResponse(BaseModel):
    payment_id: str
    status: str
    amount: float
    currency: str


@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for K8s probes."""
    return {"status": "healthy", "service": "payments"}


@app.post(
    "/process", response_model=PaymentProcessResponse, status_code=status.HTTP_201_CREATED
)
async def process_payment(payment: PaymentProcessRequest) -> Dict[str, Any]:
    """
    Process a payment request.
    Currently stores in-memory, will be persisted to PostgreSQL in M1.
    """
    payment_id = str(uuid.uuid4())

    payment_record = {
        "payment_id": payment_id,
        "status": "completed",
        "amount": payment.amount,
        "currency": payment.currency,
        "tenant_id": payment.tenant_id,
    }

    # Store in memory (temporary)
    payments_store[payment_id] = payment_record

    return {
        "payment_id": payment_id,
        "status": "completed",
        "amount": payment.amount,
        "currency": payment.currency,
    }


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str) -> Dict[str, Any]:
    """Retrieve a payment by ID."""
    if payment_id not in payments_store:
        return {"error": "payment not found"}, 404

    return payments_store[payment_id]


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "service": "resilience-lab-payments",
        "version": "0.0.1",
        "endpoints": ["/healthz", "/process", "/payments/{id}"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
