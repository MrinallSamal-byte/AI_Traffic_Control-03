import pytest
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_server.app import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'status' in data
    assert data['status'] == 'healthy'

def test_driver_score_endpoint_valid_data(client):
    """Test driver_score endpoint with valid telemetry data"""
    telemetry = {
        "device_id": "test-device-001",
        "timestamp": 1690000000,
        "speed": 50.0,
        "accel_x": 1.2,
        "accel_y": 0.3,
        "accel_z": 9.8,
        "jerk": 0.5,
        "yaw": 0.02
    }
    
    response = client.post('/driver_score', 
                          data=json.dumps(telemetry),
                          content_type='application/json')
    
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'device_id' in data
    assert 'timestamp' in data
    assert 'driver_score' in data
    assert 'model' in data
    
    assert data['device_id'] == telemetry['device_id']
    assert data['timestamp'] == telemetry['timestamp']
    assert isinstance(data['driver_score'], (int, float))
    assert 0 <= data['driver_score'] <= 100
    assert data['model'] in ['random_forest', 'heuristic']

def test_driver_score_endpoint_missing_device_id(client):
    """Test driver_score endpoint with missing device_id"""
    telemetry = {
        "timestamp": 1690000000,
        "speed": 50.0
    }
    
    response = client.post('/driver_score',
                          data=json.dumps(telemetry),
                          content_type='application/json')
    
    assert response.status_code == 400
    
    data = json.loads(response.data)
    assert 'error' in data
    assert 'device_id' in data['error']

def test_driver_score_endpoint_missing_timestamp(client):
    """Test driver_score endpoint with missing timestamp"""
    telemetry = {
        "device_id": "test-device-001",
        "speed": 50.0
    }
    
    response = client.post('/driver_score',
                          data=json.dumps(telemetry),
                          content_type='application/json')
    
    assert response.status_code == 400
    
    data = json.loads(response.data)
    assert 'error' in data
    assert 'timestamp' in data['error']

def test_driver_score_endpoint_invalid_json(client):
    """Test driver_score endpoint with invalid JSON"""
    response = client.post('/driver_score',
                          data='invalid json',
                          content_type='application/json')
    
    assert response.status_code == 400

def test_scores_endpoint(client):
    """Test scores endpoint"""
    response = client.get('/scores')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'scores' in data
    assert 'count' in data
    assert isinstance(data['scores'], list)
    assert isinstance(data['count'], int)

def test_scores_endpoint_with_limit(client):
    """Test scores endpoint with limit parameter"""
    response = client.get('/scores?limit=10')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'scores' in data
    assert len(data['scores']) <= 10