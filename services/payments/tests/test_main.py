"""Unit tests for the Payments service."""

import pytest
from fastapi.testclient import TestClient

from services.payments.main import app

client = TestClient(app)


@pytest.mark.unit
def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.unit
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "resilience-lab-payments"


@pytest.mark.unit
def test_metrics_endpoint_available():
    response = client.get("/metrics")
    assert response.status_code == 200


@pytest.mark.unit
def test_process_payment():
    payload = {"amount": 10.0, "currency": "USD", "tenant_id": "test"}
    response = client.post("/process", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["amount"] == 10.0
    assert "payment_id" in data


@pytest.mark.unit
def test_process_payment_invalid_amount():
    payload = {"amount": -1.0, "currency": "USD"}
    response = client.post("/process", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_get_payment_not_found():
    response = client.get("/payments/nonexistent-id")
    assert response.status_code == 200
    assert "error" in response.json()


@pytest.mark.unit
def test_get_payment_found():
    payload = {"amount": 25.0, "currency": "EUR"}
    create_resp = client.post("/process", json=payload)
    payment_id = create_resp.json()["payment_id"]

    response = client.get(f"/payments/{payment_id}")
    assert response.status_code == 200
    assert response.json()["payment_id"] == payment_id
