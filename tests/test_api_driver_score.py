import pytest
import requests
import json
import time

API_BASE_URL = "http://localhost:5000"

def test_health_endpoint():
    """Test that the health endpoint is working"""
    response = requests.get(f"{API_BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "api_server"

def test_driver_score_endpoint():
    """Test the driver score endpoint with valid telemetry"""
    telemetry = {
        "device_id": "TEST-001",
        "timestamp": int(time.time()),
        "speed": 50.0,
        "accel_x": 1.2,
        "accel_y": 0.3,
        "accel_z": 9.8,
        "jerk": 0.5,
        "yaw": 0.02
    }
    
    response = requests.post(
        f"{API_BASE_URL}/driver_score",
        json=telemetry,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "device_id" in data
    assert "timestamp" in data
    assert "driver_score" in data
    assert "model" in data
    
    # Check data types and ranges
    assert data["device_id"] == telemetry["device_id"]
    assert data["timestamp"] == telemetry["timestamp"]
    assert isinstance(data["driver_score"], (int, float))
    assert 0 <= data["driver_score"] <= 100
    assert data["model"] in ["random_forest", "heuristic"]

def test_driver_score_missing_fields():
    """Test driver score endpoint with missing required fields"""
    # Missing device_id
    telemetry = {
        "timestamp": int(time.time()),
        "speed": 50.0
    }
    
    response = requests.post(
        f"{API_BASE_URL}/driver_score",
        json=telemetry
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "device_id" in data["error"]

def test_driver_score_invalid_json():
    """Test driver score endpoint with invalid JSON"""
    response = requests.post(
        f"{API_BASE_URL}/driver_score",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data

def test_driver_score_high_risk_scenario():
    """Test high-risk driving scenario produces reasonable score"""
    high_risk_telemetry = {
        "device_id": "TEST-HIGH-RISK",
        "timestamp": int(time.time()),
        "speed": 120.0,  # High speed
        "accel_x": 8.0,  # Harsh acceleration
        "accel_y": 3.0,  # High lateral acceleration
        "accel_z": 9.8,
        "jerk": 5.0,     # High jerk
        "yaw": 0.5       # High yaw rate
    }
    
    response = requests.post(
        f"{API_BASE_URL}/driver_score",
        json=high_risk_telemetry
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # High-risk scenario should produce a higher score
    assert data["driver_score"] > 20  # Should be significantly above minimum

def test_driver_score_low_risk_scenario():
    """Test low-risk driving scenario produces reasonable score"""
    low_risk_telemetry = {
        "device_id": "TEST-LOW-RISK",
        "timestamp": int(time.time()),
        "speed": 30.0,   # Low speed
        "accel_x": 0.1,  # Gentle acceleration
        "accel_y": 0.1,  # Low lateral acceleration
        "accel_z": 9.8,
        "jerk": 0.1,     # Low jerk
        "yaw": 0.01      # Low yaw rate
    }
    
    response = requests.post(
        f"{API_BASE_URL}/driver_score",
        json=low_risk_telemetry
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Low-risk scenario should produce a lower score
    assert data["driver_score"] < 80  # Should be well below maximum

if __name__ == "__main__":
    # Run tests manually if API server is running
    print("Testing API endpoints...")
    try:
        test_health_endpoint()
        print("✓ Health endpoint test passed")
        
        test_driver_score_endpoint()
        print("✓ Driver score endpoint test passed")
        
        test_driver_score_missing_fields()
        print("✓ Missing fields test passed")
        
        test_driver_score_invalid_json()
        print("✓ Invalid JSON test passed")
        
        test_driver_score_high_risk_scenario()
        print("✓ High risk scenario test passed")
        
        test_driver_score_low_risk_scenario()
        print("✓ Low risk scenario test passed")
        
        print("\nAll tests passed! 🎉")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure the API server is running on http://localhost:5000")