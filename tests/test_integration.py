"""Integration tests for Resilience Lab services."""

import pytest
import requests
import time

API_BASE = "http://localhost:8000"
PAYMENTS_BASE = "http://localhost:8001"


def wait_for_service(url: str, timeout: int = 30):
    """Wait for service to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{url}/healthz")
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            time.sleep(1)
    return False


class TestServiceHealth:
    """Test service health endpoints."""

    def test_api_health(self):
        """Test API service is healthy."""
        assert wait_for_service(API_BASE), "API service not ready"
        response = requests.get(f"{API_BASE}/healthz")
        assert response.status_code == 200

    def test_payments_health(self):
        """Test Payments service is healthy."""
        assert wait_for_service(PAYMENTS_BASE), "Payments service not ready"
        response = requests.get(f"{PAYMENTS_BASE}/healthz")
        assert response.status_code == 200


class TestPaymentFlow:
    """Test payment processing flow."""

    def test_payment_endpoint(self):
        """Test /process endpoint accepts payment request."""
        payload = {"amount": 100, "currency": "USD"}
        response = requests.post(f"{PAYMENTS_BASE}/process", json=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "payment_id" in data
        assert "status" in data
        assert data["status"] == "completed"

    def test_payment_validation(self):
        """Test payment endpoint validates input."""
        # Test with invalid amount
        payload = {"amount": -50, "currency": "USD"}
        response = requests.post(f"{PAYMENTS_BASE}/process", json=payload)
        # Should reject negative amounts
        assert response.status_code in [400, 422]
