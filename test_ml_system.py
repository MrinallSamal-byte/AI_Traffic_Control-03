#!/usr/bin/env python3
"""
Test script for ML driver scoring system
"""
import requests
import json
import time

def test_driver_score_api():
    """Test the driver score API endpoint"""
    url = "http://localhost:5000/driver_score"
    
    # Test data
    test_telemetry = {
        "device_id": "test-device-001",
        "timestamp": int(time.time()),
        "speed": 65.5,
        "accel_x": 2.1,
        "accel_y": -0.5,
        "accel_z": 9.8,
        "jerk": 0.8,
        "yaw": 0.02
    }
    
    try:
        response = requests.post(url, json=test_telemetry, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✓ API Test Successful!")
            print(f"  Device: {data.get('device_id')}")
            print(f"  Score: {data.get('driver_score'):.2f}")
            print(f"  Model: {data.get('model')}")
            return True
        else:
            print(f"✗ API Test Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ API Test Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing ML Driver Scoring System...")
    test_driver_score_api()