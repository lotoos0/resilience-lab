"""
Sanity tests to ensure CI pipeline is working.
These will be expanded in M0 with actual service tests.
"""


def test_sanity():
    """Basic sanity check - CI should pass."""
    assert 1 + 1 == 2


def test_imports():
    """Verify core dependencies are installed."""
    import fastapi
    import pytest
    import redis
    import psycopg2

    assert fastapi is not None
    assert pytest is not None
