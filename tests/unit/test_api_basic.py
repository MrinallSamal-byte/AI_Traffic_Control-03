"""Basic API tests for health checks and authentication."""

import pytest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api_server.app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'api_server'


@patch('api_server.app.get_db')
def test_register_success(mock_get_db, client):
    """Test successful user registration."""
    # Mock database
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock user doesn't exist
    mock_cursor.fetchone.side_effect = [None, {'user_id': 1, 'name': 'Test', 'email': 'test@example.com'}]
    
    response = client.post('/api/v1/auth/register', 
                          json={'name': 'Test User', 'email': 'test@example.com'})
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'access_token' in data
    assert data['user']['email'] == 'test@example.com'


def test_register_missing_fields(client):
    """Test registration with missing fields."""
    response = client.post('/api/v1/auth/register', json={'name': 'Test'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


@patch('api_server.app.get_db')
def test_login_success(mock_get_db, client):
    """Test successful login."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock user exists
    mock_cursor.fetchone.return_value = {'user_id': 1, 'email': 'test@example.com'}
    
    response = client.post('/api/v1/auth/login',
                          json={'email': 'test@example.com', 'password': 'password'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data


def test_login_missing_credentials(client):
    """Test login with missing credentials."""
    response = client.post('/api/v1/auth/login', json={'email': 'test@example.com'})
    assert response.status_code == 400