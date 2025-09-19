import pytest
import json
import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api_server'))

from api_server.app import app

@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_driver_score_endpoint(client):
    """Test POST /driver_score endpoint."""
    telemetry = {
        "device_id": "test_device_123",
        "timestamp": 1699123456,
        "speed": 45.5,
        "accel_x": 1.2,
        "accel_y": 0.3,
        "accel_z": 9.8,
        "jerk": 0.5,
        "yaw": 0.02
    }
    
    response = client.post('/driver_score', 
                          json=telemetry,
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Check response structure
    assert 'device_id' in data
    assert 'timestamp' in data
    assert 'driver_score' in data
    assert 'model' in data
    
    # Check data types and ranges
    assert data['device_id'] == telemetry['device_id']
    assert data['timestamp'] == telemetry['timestamp']
    assert isinstance(data['driver_score'], (int, float))
    assert 0 <= data['driver_score'] <= 100
    assert data['model'] in ['random_forest', 'heuristic']

def test_driver_score_missing_device_id(client):
    """Test driver_score with missing device_id."""
    telemetry = {
        "timestamp": 1699123456,
        "speed": 45.5
    }
    
    response = client.post('/driver_score', json=telemetry)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_driver_score_invalid_json(client):
    """Test driver_score with invalid JSON."""
    response = client.post('/driver_score', 
                          data="invalid json",
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data