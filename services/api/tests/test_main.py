"""Unit tests for the API service entrypoint."""

import pytest
from fastapi.testclient import TestClient

from ..main import app

client = TestClient(app)


@pytest.mark.unit
def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "api"}


@pytest.mark.unit
def test_metrics_endpoint_available():
    response = client.get("/metrics")
    assert response.status_code == 200
