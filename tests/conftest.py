"""Pytest configuration and shared fixtures."""

import pytest
import os
import tempfile
from unittest.mock import MagicMock


@pytest.fixture(scope="session")
def test_db():
    """Create test database connection."""
    # In a real implementation, this would create a test database
    mock_db = MagicMock()
    yield mock_db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return MagicMock()


@pytest.fixture
def sample_telemetry():
    """Sample telemetry data for testing."""
    return {
        "deviceId": "TEST_DEVICE_001",
        "timestamp": "2024-01-15T10:30:00Z",
        "location": {"lat": 1.3521, "lon": 103.8198},
        "speedKmph": 45.2,
        "heading": 90,
        "acceleration": {"x": 0.1, "y": 0.0, "z": 9.8}
    }


@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {
        "user_id": 1,
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+65-1234-5678"
    }