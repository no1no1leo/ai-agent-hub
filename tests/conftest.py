"""
Shared pytest fixtures for AI Agent Hub test suite.
"""
import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.hub_market import HubMarket
from fastapi.testclient import TestClient
from marketplace.api import app


@pytest.fixture(scope="function")
def fresh_market():
    """Return a new, isolated HubMarket instance for each test."""
    return HubMarket()


@pytest.fixture(scope="function")
def sample_task(fresh_market):
    """Create a sample task in a fresh market and return (market, task)."""
    task = fresh_market.create_task(
        description="Sample task for testing",
        input_data="sample_input.csv",
        max_budget=1.0,
        expected_tokens=1000,
        requester_id="test_requester",
    )
    return fresh_market, task


@pytest.fixture(scope="function")
def test_client():
    """Return a FastAPI TestClient for the marketplace API."""
    with TestClient(app) as client:
        yield client
