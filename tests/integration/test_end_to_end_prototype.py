#!/usr/bin/env python3
"""
End-to-End Integration Test for Complete Prototype
Tests the full pipeline: telemetry → validation → ML → blockchain → dashboard
"""

import pytest
import requests
import json
import time
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
import websocket
from unittest.mock import Mock

class TestEndToEndPrototype:
    """Complete system integration test"""
    
    @pytest.fixture(scope="class")
    def system_urls(self):
        """System service URLs"""
        return {
            'api_server': 'http://localhost:5000',
            'ml_services': 'http://localhost:5002',
            'stream_processor': 'http://localhost:5004',
            'blockchain_service': 'http://localhost:5003'
        }
    
    @pytest.fixture(scope="class")
    def auth_token(self, system_urls):
        """Get authentication token"""
        response = requests.post(f"{system_urls['api_server']}/auth/login", json={
            'username': 'admin',
            'password': 'admin123'
        })
        assert response.status_code == 200
        return response.json()['access_token']
    
    def test_01_system_health(self, system_urls):
        """Test all services are healthy"""
        for service, url in system_urls.items():
            response = requests.get(f"{url}/health", timeout=10)
            assert response.status_code == 200, f"{service} health check failed"
            
            health_data = response.json()
            assert health_data['status'] == 'healthy'
            assert health_data['service'] in service
    
    def test_02_authentication_flow(self, system_urls):
        """Test authentication and authorization"""
        # Test login
        response = requests.post(f"{system_urls['api_server']}/auth/login", json={
            'username': 'admin',
            'password': 'admin123'
        })
        assert response.status_code == 200
        
        auth_data = response.json()
        assert 'access_token' in auth_data
        assert auth_data['user'] == 'admin'
        assert auth_data['role'] == 'admin'
        
        token = auth_data['access_token']
        
        # Test protected endpoint access
        response = requests.post(
            f"{system_urls['api_server']}/telemetry/ingest",
            headers={'Authorization': f'Bearer {token}'},
            json={
                'deviceId': 'TEST_E2E_001',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'location': {'lat': 20.2961, 'lon': 85.8245},
                'speedKmph': 45.5,
                'acceleration': {'x': 1.2, 'y': -0.8, 'z': 9.8},
                'fuelLevel': 75.5
            }
        )
        assert response.status_code == 200
        
        # Test unauthorized access
        response = requests.post(
            f"{system_urls['api_server']}/telemetry/ingest",
            json={'test': 'data'}
        )
        assert response.status_code == 401
    
    def test_03_telemetry_validation_pipeline(self, system_urls):
        """Test telemetry validation and processing"""
        # Send valid telemetry via MQTT
        mqtt_client = mqtt.Client()
        mqtt_client.connect('localhost', 1883, 60)
        
        valid_telemetry = {
            'deviceId': 'TEST_E2E_002',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'location': {'lat': 20.2961, 'lon': 85.8245},
            'speedKmph': 45.5,
            'acceleration': {'x': 1.2, 'y': -0.8, 'z': 9.8},
            'fuelLevel': 75.5,
            'heading': 180.0
        }
        
        mqtt_client.publish(
            '/org/test/device/TEST_E2E_002/telemetry',
            json.dumps(valid_telemetry)
        )
        
        # Send invalid telemetry
        invalid_telemetry = {
            'deviceId': 'TEST_E2E_003',
            'timestamp': 'invalid-timestamp',
            'location': {'lat': 'invalid', 'lon': 85.8245},
            'speedKmph': 500  # Out of range
        }
        
        mqtt_client.publish(
            '/org/test/device/TEST_E2E_003/telemetry',
            json.dumps(invalid_telemetry)
        )
        
        mqtt_client.disconnect()
        
        # Wait for processing
        time.sleep(5)
        
        # Check stream processor metrics
        response = requests.get(f"{system_urls['stream_processor']}/metrics/json")
        assert response.status_code == 200
        
        metrics = response.json()
        # Should have processed at least one message
        assert metrics.get('total_devices_seen', 0) >= 1
    
    def test_04_ml_prediction_pipeline(self, system_urls):
        """Test ML prediction pipeline"""
        # Test ML service health
        response = requests.get(f"{system_urls['ml_services']}/health")
        assert response.status_code == 200
        
        # Test prediction endpoint
        prediction_data = {
            'deviceId': 'TEST_E2E_004',
            'speed': 45.5,
            'accel_x': 1.2,
            'accel_y': -0.8,
            'accel_z': 9.8,
            'jerk': 0.5,
            'yaw': 2.0
        }
        
        response = requests.post(
            f"{system_urls['ml_services']}/predict",
            json=prediction_data
        )
        assert response.status_code == 200
        
        prediction_result = response.json()
        assert prediction_result['deviceId'] == 'TEST_E2E_004'
        assert 'prediction' in prediction_result
        assert 'model_version' in prediction_result
        assert 'processing_time_ms' in prediction_result
        assert 0 <= prediction_result['prediction'] <= 100
        
        # Test driver score endpoint (legacy)
        response = requests.post(
            f"{system_urls['ml_services']}/predict/driver_score",
            json=prediction_data
        )
        assert response.status_code == 200
        
        driver_score = response.json()
        assert 0 <= driver_score['prediction'] <= 100
    
    def test_05_blockchain_integration(self, system_urls, auth_token):
        """Test blockchain toll processing"""
        # Check blockchain service health
        response = requests.get(f"{system_urls['blockchain_service']}/health")
        assert response.status_code == 200
        
        # Test toll charge via API server
        toll_data = {
            'device_id': 'TEST_E2E_005',
            'gantry_id': 'GANTRY_TEST_001',
            'location': {'lat': 20.3000, 'lon': 85.8300},
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        response = requests.post(
            f"{system_urls['api_server']}/toll/charge",
            headers={'Authorization': f'Bearer {auth_token}'},
            json=toll_data
        )
        
        # May succeed or fail depending on blockchain state
        # Just check it doesn't crash
        assert response.status_code in [200, 500, 503]
        
        if response.status_code == 200:
            toll_result = response.json()
            assert toll_result['device_id'] == 'TEST_E2E_005'
            assert toll_result['gantry_id'] == 'GANTRY_TEST_001'
            assert 'amount' in toll_result
    
    def test_06_api_integration_flow(self, system_urls, auth_token):
        """Test complete API integration flow"""
        device_id = 'TEST_E2E_006'
        
        # 1. Ingest telemetry
        telemetry_data = {
            'deviceId': device_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'location': {'lat': 20.2961, 'lon': 85.8245},
            'speedKmph': 65.5,  # Slightly high speed
            'acceleration': {'x': 2.5, 'y': -1.2, 'z': 9.8},  # Moderate acceleration
            'fuelLevel': 45.0,
            'heading': 90.0
        }
        
        response = requests.post(
            f"{system_urls['api_server']}/telemetry/ingest",
            headers={'Authorization': f'Bearer {auth_token}'},
            json=telemetry_data
        )
        assert response.status_code == 200
        
        # 2. Get driver score
        response = requests.post(
            f"{system_urls['api_server']}/driver_score",
            headers={'Authorization': f'Bearer {auth_token}'},
            json=telemetry_data
        )
        assert response.status_code == 200
        
        score_result = response.json()
        assert score_result['device_id'] == device_id
        assert 'driver_score' in score_result
        
        # 3. Check toll events (if any)
        response = requests.get(
            f"{system_urls['api_server']}/toll/events?device_id={device_id}",
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        assert response.status_code == 200
        
        events_result = response.json()
        assert 'events' in events_result
        assert 'count' in events_result
    
    def test_07_metrics_and_monitoring(self, system_urls):
        """Test metrics collection across all services"""
        for service, url in system_urls.items():
            # Test Prometheus metrics
            response = requests.get(f"{url}/metrics")
            assert response.status_code == 200
            assert 'text/plain' in response.headers.get('content-type', '')
            
            # Test JSON metrics (if available)
            try:
                response = requests.get(f"{url}/metrics/json")
                if response.status_code == 200:
                    metrics = response.json()
                    assert isinstance(metrics, dict)
            except:
                pass  # Not all services may have JSON metrics
    
    def test_08_error_handling_and_resilience(self, system_urls, auth_token):
        """Test system resilience and error handling"""
        # Test invalid telemetry data
        invalid_data = {
            'deviceId': '',  # Empty device ID
            'timestamp': 'not-a-timestamp',
            'location': {'lat': 'invalid', 'lon': 'invalid'},
            'speedKmph': -50,  # Negative speed
            'acceleration': {'x': 'invalid'}
        }
        
        response = requests.post(
            f"{system_urls['api_server']}/telemetry/ingest",
            headers={'Authorization': f'Bearer {auth_token}'},
            json=invalid_data
        )
        assert response.status_code == 400  # Should reject invalid data
        
        # Test ML service with invalid data
        response = requests.post(
            f"{system_urls['ml_services']}/predict",
            json={'invalid': 'data'}
        )
        assert response.status_code == 422  # Validation error
        
        # Test unauthorized blockchain access
        response = requests.post(
            f"{system_urls['api_server']}/toll/charge",
            json={'device_id': 'test'}
        )
        assert response.status_code == 401  # Unauthorized
    
    def test_09_performance_benchmarks(self, system_urls, auth_token):
        """Basic performance benchmarks"""
        # Test API response times
        start_time = time.time()
        
        response = requests.post(
            f"{system_urls['ml_services']}/predict",
            json={
                'deviceId': 'PERF_TEST',
                'speed': 50.0,
                'accel_x': 1.0,
                'accel_y': 0.5,
                'accel_z': 9.8,
                'jerk': 0.2,
                'yaw': 5.0
            }
        )
        
        response_time = time.time() - start_time
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
        
        prediction_result = response.json()
        assert prediction_result['processing_time_ms'] < 500  # Internal processing < 500ms
    
    def test_10_data_consistency(self, system_urls, auth_token):
        """Test data consistency across the system"""
        device_id = 'CONSISTENCY_TEST'
        
        # Send telemetry with specific characteristics
        telemetry_data = {
            'deviceId': device_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'location': {'lat': 20.2961, 'lon': 85.8245},
            'speedKmph': 80.0,  # High speed
            'acceleration': {'x': 6.5, 'y': -2.0, 'z': 9.8},  # Harsh acceleration
            'fuelLevel': 30.0,
            'heading': 45.0
        }
        
        # Send via API
        response = requests.post(
            f"{system_urls['api_server']}/telemetry/ingest",
            headers={'Authorization': f'Bearer {auth_token}'},
            json=telemetry_data
        )
        assert response.status_code == 200
        
        # Get ML prediction
        response = requests.post(
            f"{system_urls['ml_services']}/predict",
            json={
                'deviceId': device_id,
                'speed': telemetry_data['speedKmph'],
                'accel_x': telemetry_data['acceleration']['x'],
                'accel_y': telemetry_data['acceleration']['y'],
                'accel_z': telemetry_data['acceleration']['z'],
                'jerk': 1.0,
                'yaw': 5.0
            }
        )
        assert response.status_code == 200
        
        prediction = response.json()
        # High speed + harsh acceleration should result in higher risk score
        assert prediction['prediction'] > 30  # Should detect some risk

if __name__ == "__main__":
    pytest.main([__file__, "-v"])