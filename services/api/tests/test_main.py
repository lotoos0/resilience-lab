"""Unit tests for the API service entrypoint."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from ..main import app, redis_client

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


@pytest.mark.unit
def test_root():
    """`/` is rate-limited like any other endpoint, so mock Redis for the check."""
    mock_pipeline = Mock()
    mock_pipeline.execute.return_value = [0, 0, True, True]
    with patch.object(redis_client, "pipeline", return_value=mock_pipeline):
        response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "service": "resilience-lab-api",
        "version": "0.0.1",
        "endpoints": ["/healthz", "/pay"],
    }
