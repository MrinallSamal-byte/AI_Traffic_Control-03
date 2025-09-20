#!/usr/bin/env python3
"""
Test script to verify the MVP prototype end-to-end flow
"""

import sys
import os
import time
import requests
import threading
from datetime import datetime

# Add current directory to path
sys.path.append('.')

def test_ml_service():
    """Test the ML service directly"""
    print("1. Testing ML service...")
    try:
        from ml_services.driver_score import predict_score
        
        telemetry = {
            'device_id': 'TEST-001',
            'timestamp': int(time.time()),
            'speed': 50.0,
            'accel_x': 1.2,
            'accel_y': 0.3,
            'accel_z': 9.8,
            'jerk': 0.5,
            'yaw': 0.02
        }
        
        result = predict_score(telemetry)
        print(f"   [OK] ML service working: score={result['score']:.2f}, model={result['model']}")
        return True
    except Exception as e:
        print(f"   [ERROR] ML service failed: {e}")
        return False

def test_api_server():
    """Test if API server is running"""
    print("2. Testing API server...")
    try:
        response = requests.get("http://localhost:5000/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] API server healthy: {data}")
            return True
        else:
            print(f"   [ERROR] API server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"   [ERROR] API server not reachable: {e}")
        return False

def test_driver_score_api():
    """Test the driver score API endpoint"""
    print("3. Testing driver score API...")
    try:
        telemetry = {
            "device_id": "TEST-API-001",
            "timestamp": int(time.time()),
            "speed": 65.0,
            "accel_x": 2.1,
            "accel_y": 0.5,
            "accel_z": 9.8,
            "jerk": 1.2,
            "yaw": 0.05
        }
        
        response = requests.post(
            "http://localhost:5000/driver_score",
            json=telemetry,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Driver score API working: score={data['driver_score']:.2f}, model={data['model']}")
            return True
        else:
            print(f"   [ERROR] Driver score API returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   [ERROR] Driver score API failed: {e}")
        return False

def test_simulator():
    """Test the simulator"""
    print("4. Testing simulator...")
    try:
        from device_simulator.simulator import VehicleSimulator
        
        # Create a simulator instance
        sim = VehicleSimulator(device_id="TEST-SIM-001", mode="http")
        
        # Generate test telemetry
        telemetry = sim._generate_telemetry()
        print(f"   [OK] Simulator generates telemetry: device_id={telemetry['device_id']}, speed={telemetry['speed']}")
        return True
    except Exception as e:
        print(f"   [ERROR] Simulator failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing MVP Prototype Components\n")
    
    tests = [
        test_ml_service,
        test_api_server,
        test_driver_score_api,
        test_simulator
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All components working! MVP prototype is ready.")
        print("\nTo run the full demo:")
        print("1. python ml_services/train_model.py")
        print("2. python api_server/app.py")
        print("3. python device_simulator/simulator.py --devices 3")
        print("4. python -m http.server 3000 (then open http://localhost:3000/dashboard/simple_demo.html)")
    else:
        print("[ERROR] Some components need attention. Check the errors above.")

if __name__ == "__main__":
    main()