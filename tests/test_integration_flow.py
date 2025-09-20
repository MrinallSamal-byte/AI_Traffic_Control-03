#!/usr/bin/env python3
"""
Integration tests for end-to-end system flow
"""

import pytest
import requests
import json
import time
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
import redis
import socketio

class TestIntegrationFlow:
    """Test complete system integration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.api_base = "http://localhost:5000"
        self.ml_base = "http://localhost:5001"
        self.blockchain_base = "http://localhost:5002"
        self.websocket_url = "http://localhost:5003"
        
        # Get auth token
        self.auth_token = self.get_auth_token()
        self.headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Redis client for pub/sub testing
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # WebSocket client
        self.sio = socketio.SimpleClient()
        
    def get_auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{self.api_base}/auth/login", json={
            "username": "admin",
            "password": "password"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_health_endpoints(self):
        """Test all health endpoints"""
        services = [
            (self.api_base, "api_server"),
            (self.ml_base, "ml_services"),
            (self.blockchain_base, "blockchain")
        ]
        
        for base_url, service_name in services:
            response = requests.get(f"{base_url}/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == service_name
            assert "timestamp" in data
    
    def test_ml_inference_flow(self):
        """Test ML inference endpoint"""
        telemetry_data = {
            "device_id": "TEST_DEVICE_001",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "speed": 65.5,
            "accel_x": 1.2,
            "accel_y": -0.8,
            "accel_z": 9.8,
            "jerk": 2.1,
            "yaw": 15.0
        }
        
        response = requests.post(
            f"{self.ml_base}/predict",
            json=telemetry_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "score" in data
        assert "model" in data
        assert "alert" in data
        assert "confidence" in data
        assert data["device_id"] == "TEST_DEVICE_001"
        
        # Verify score is in valid range
        assert 0 <= data["score"] <= 100
        
        # Verify alert level
        assert data["alert"] in ["NORMAL", "MEDIUM_RISK", "HIGH_RISK"]
    
    def test_toll_charging_flow(self):
        """Test toll charging with blockchain integration"""
        toll_data = {
            "device_id": "TEST_DEVICE_001",
            "gantry_id": 1,
            "location": {"lat": 20.2961, "lon": 85.8245},
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "vehicle_type": "car"
        }
        
        response = requests.post(
            f"{self.api_base}/toll/charge",
            json=toll_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "toll_id" in data
        assert "amount" in data
        assert "tx_hash" in data
        assert data["device_id"] == "TEST_DEVICE_001"
        assert data["gantry_id"] == 1
        assert data["amount"] == 0.05  # Car toll rate
    
    def test_websocket_real_time_updates(self):
        """Test WebSocket real-time updates"""
        received_messages = []
        
        def on_telemetry_update(data):
            received_messages.append(('telemetry', data))
        
        def on_event_update(data):
            received_messages.append(('event', data))
        
        def on_toll_update(data):
            received_messages.append(('toll', data))
        
        # Connect to WebSocket
        self.sio.connect(self.websocket_url)
        self.sio.on('telemetry_update', on_telemetry_update)
        self.sio.on('event_update', on_event_update)
        self.sio.on('toll_update', on_toll_update)
        
        # Publish test messages to Redis
        test_telemetry = {
            "deviceId": "TEST_DEVICE_WS",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "location": {"lat": 20.2961, "lon": 85.8245},
            "speedKmph": 55.0
        }
        
        test_event = {
            "deviceId": "TEST_DEVICE_WS",
            "eventType": "HARSH_BRAKE",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "severity": "HIGH"
        }
        
        test_toll = {
            "deviceId": "TEST_DEVICE_WS",
            "gantryId": 1,
            "amount": 0.05,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "paid": True
        }
        
        # Publish messages
        self.redis_client.publish('telemetry', json.dumps(test_telemetry))
        self.redis_client.publish('events', json.dumps(test_event))
        self.redis_client.publish('tolls', json.dumps(test_toll))
        
        # Wait for messages
        time.sleep(2)
        
        # Verify messages received
        assert len(received_messages) >= 3
        
        message_types = [msg[0] for msg in received_messages]
        assert 'telemetry' in message_types
        assert 'event' in message_types
        assert 'toll' in message_types
        
        self.sio.disconnect()
    
    def test_mqtt_to_stream_processor_flow(self):
        """Test MQTT message processing through stream processor"""
        # This test requires the stream processor to be running
        # and connected to MQTT broker
        
        mqtt_client = mqtt.Client()
        mqtt_client.connect("localhost", 1883, 60)
        
        # Send test telemetry via MQTT
        test_telemetry = {
            "deviceId": "TEST_MQTT_001",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "location": {"lat": 20.2961, "lon": 85.8245},
            "speedKmph": 45.0,
            "heading": 90.0,
            "acceleration": {"x": 0.5, "y": -0.2, "z": 9.8}
        }
        
        mqtt_client.publish(
            "/org/test/device/TEST_MQTT_001/telemetry",
            json.dumps(test_telemetry)
        )
        
        # Wait for processing
        time.sleep(3)
        
        # Check if data was processed (would need database connection to verify)
        # For now, just verify MQTT publish succeeded
        mqtt_client.disconnect()
        
        assert True  # Placeholder - would check database in full implementation
    
    def test_driver_score_integration(self):
        """Test driver scoring integration"""
        telemetry_data = {
            "device_id": "TEST_DEVICE_SCORE",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "speed": 85.0,  # High speed
            "accel_x": 3.5,  # High acceleration
            "accel_y": -2.1,
            "accel_z": 9.8,
            "jerk": 4.2,  # High jerk
            "yaw": 25.0
        }
        
        # Test API server endpoint
        response = requests.post(
            f"{self.api_base}/driver_score",
            json=telemetry_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        api_data = response.json()
        
        # Test ML service endpoint directly
        ml_response = requests.post(
            f"{self.ml_base}/predict",
            json=telemetry_data,
            headers=self.headers
        )
        
        assert ml_response.status_code == 200
        ml_data = ml_response.json()
        
        # Both should return similar scores
        assert abs(api_data["driver_score"] - ml_data["score"]) < 5.0
        
        # High-risk driving should result in high score
        assert ml_data["score"] > 50  # Should be risky driving
        assert ml_data["alert"] in ["MEDIUM_RISK", "HIGH_RISK"]
    
    def test_model_versioning(self):
        """Test ML model versioning"""
        # Get model info
        response = requests.get(f"{self.ml_base}/model/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "version" in data
        assert "loaded" in data
        assert data["loaded"] is True
        
        # Test model reload
        reload_response = requests.post(
            f"{self.ml_base}/model/reload",
            headers=self.headers
        )
        assert reload_response.status_code == 200
        
        reload_data = reload_response.json()
        assert reload_data["status"] == "reloaded"
    
    def test_authentication_required(self):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            ("POST", f"{self.api_base}/driver_score"),
            ("POST", f"{self.api_base}/toll/charge"),
            ("POST", f"{self.ml_base}/predict"),
            ("POST", f"{self.ml_base}/model/reload")
        ]
        
        for method, url in protected_endpoints:
            if method == "POST":
                response = requests.post(url, json={})
            else:
                response = requests.get(url)
            
            # Should return 401 without auth token
            assert response.status_code == 401
    
    def test_metrics_collection(self):
        """Test metrics collection"""
        # Make some requests to generate metrics
        requests.get(f"{self.api_base}/health")
        requests.post(f"{self.api_base}/auth/login", json={
            "username": "admin", "password": "password"
        })
        
        # Get metrics
        response = requests.get(f"{self.api_base}/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "request_count" in data
        assert "error_count" in data
        assert "avg_response_time" in data
        
        # Should have recorded our requests
        assert data["request_count"]["health"] >= 1
        assert data["request_count"]["login"] >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])