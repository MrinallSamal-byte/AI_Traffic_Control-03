#!/usr/bin/env python3
"""
Enhanced unit tests for ML serving API
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import sys
import os

# Add ml_services to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'ml_services'))

from serve import app, load_model, prepare_features_array, heuristic_risk_score

class TestMLServingAPI:
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def valid_telemetry(self):
        """Valid telemetry data"""
        return {
            "deviceId": "TEST_DEVICE_001",
            "speed": 45.5,
            "accel_x": 1.2,
            "accel_y": -0.8,
            "accel_z": 9.8,
            "jerk": 0.5,
            "yaw": 2.0
        }
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ml_services"
        assert "timestamp" in data
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
    
    def test_metrics_json_endpoint(self, client):
        """Test JSON metrics endpoint"""
        response = client.get("/metrics/json")
        assert response.status_code == 200
        
        data = response.json()
        assert "request_count" in data
        assert "error_count" in data
        assert "models_loaded" in data
    
    @patch('serve.load_model')
    def test_predict_endpoint_with_ml_model(self, mock_load_model, client, valid_telemetry):
        """Test prediction endpoint with ML model"""
        # Mock model
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.7, 0.3]])
        
        mock_scaler = Mock()
        mock_scaler.transform.return_value = [[1, 2, 3, 4, 5, 6, 7, 8, 9]]
        
        mock_load_model.return_value = {
            'model': {
                'model': mock_model,
                'scaler': mock_scaler,
                'feature_names': ['speed', 'accel_x', 'accel_y', 'accel_z', 'jerk', 'yaw']
            }
        }
        
        response = client.post("/predict", json=valid_telemetry)
        assert response.status_code == 200
        
        data = response.json()
        assert data["deviceId"] == "TEST_DEVICE_001"
        assert "prediction" in data
        assert data["model_version"] == "random_forest_v1"
        assert "confidence" in data
        assert "processing_time_ms" in data
    
    @patch('serve.load_model')
    def test_predict_endpoint_fallback_to_heuristic(self, mock_load_model, client, valid_telemetry):
        """Test prediction endpoint falls back to heuristic when ML model fails"""
        mock_load_model.side_effect = Exception("Model loading failed")
        
        response = client.post("/predict", json=valid_telemetry)
        assert response.status_code == 200
        
        data = response.json()
        assert data["deviceId"] == "TEST_DEVICE_001"
        assert data["model_version"] == "heuristic_v1"
        assert data["confidence"] is None
    
    def test_predict_endpoint_invalid_input(self, client):
        """Test prediction endpoint with invalid input"""
        invalid_data = {
            "deviceId": "TEST_DEVICE_001",
            "speed": -10,  # Invalid speed
            "accel_x": 1.2
            # Missing required fields
        }
        
        response = client.post("/predict", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_driver_score_endpoint(self, client, valid_telemetry):
        """Test driver score endpoint (legacy)"""
        with patch('serve.load_model') as mock_load_model:
            mock_load_model.side_effect = Exception("Model loading failed")
            
            response = client.post("/predict/driver_score", json=valid_telemetry)
            assert response.status_code == 200
            
            data = response.json()
            assert data["deviceId"] == "TEST_DEVICE_001"
            # Driver score should be inverse of risk score
            assert 0 <= data["prediction"] <= 100
    
    def test_harsh_driving_endpoint(self, client, valid_telemetry):
        """Test harsh driving prediction endpoint"""
        response = client.post("/predict/harsh_driving", json=valid_telemetry)
        assert response.status_code == 200
        
        data = response.json()
        assert data["deviceId"] == "TEST_DEVICE_001"
        assert 0 <= data["prediction"] <= 100
    
    def test_list_models_endpoint(self, client):
        """Test list models endpoint"""
        response = client.get("/models")
        assert response.status_code == 200
        
        data = response.json()
        assert "models" in data
    
    @patch('serve.load_model')
    def test_reload_model_endpoint(self, mock_load_model, client):
        """Test model reload endpoint"""
        mock_load_model.return_value = {
            'model': Mock(),
            'loaded_at': Mock(),
            'path': '/test/path'
        }
        mock_load_model.return_value['loaded_at'].isoformat.return_value = "2024-01-01T00:00:00"
        
        response = client.post("/models/test_model/reload")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "loaded_at" in data

class TestUtilityFunctions:
    
    def test_prepare_features_array(self):
        """Test feature array preparation"""
        from serve import TelemetryInput
        
        telemetry = TelemetryInput(
            deviceId="TEST_001",
            speed=50.0,
            accel_x=1.0,
            accel_y=2.0,
            accel_z=9.8,
            jerk=0.5,
            yaw=10.0
        )
        
        features = prepare_features_array(telemetry)
        
        # Should have 9 features (6 original + 3 derived)
        assert len(features) == 9
        assert features[0] == 50.0  # speed
        assert features[1] == 1.0   # accel_x
        assert features[2] == 2.0   # accel_y
        assert features[3] == 9.8   # accel_z
        assert features[4] == 0.5   # jerk
        assert features[5] == 10.0  # yaw
        # Derived features: accel_magnitude, lateral_accel, speed_accel_ratio
        assert features[6] > 0  # accel_magnitude
        assert features[7] > 0  # lateral_accel
        assert features[8] > 0  # speed_accel_ratio
    
    def test_heuristic_risk_score(self):
        """Test heuristic risk scoring"""
        from serve import TelemetryInput
        
        # Normal driving
        normal_telemetry = TelemetryInput(
            deviceId="TEST_001",
            speed=30.0,
            accel_x=0.5,
            accel_y=0.3,
            accel_z=9.8,
            jerk=0.1,
            yaw=1.0
        )
        
        normal_score = heuristic_risk_score(normal_telemetry)
        assert 0 <= normal_score <= 100
        
        # Harsh driving
        harsh_telemetry = TelemetryInput(
            deviceId="TEST_001",
            speed=80.0,
            accel_x=5.0,
            accel_y=4.0,
            accel_z=9.8,
            jerk=3.0,
            yaw=15.0
        )
        
        harsh_score = heuristic_risk_score(harsh_telemetry)
        assert harsh_score > normal_score
        assert 0 <= harsh_score <= 100
    
    @patch('serve.joblib.load')
    @patch('serve.os.path.exists')
    def test_load_model_success(self, mock_exists, mock_joblib_load):
        """Test successful model loading"""
        mock_exists.return_value = True
        mock_model = Mock()
        mock_joblib_load.return_value = mock_model
        
        result = load_model('test_model')
        
        assert result is not None
        assert 'model' in result
        assert 'loaded_at' in result
        assert 'path' in result
    
    @patch('serve.os.path.exists')
    def test_load_model_file_not_found(self, mock_exists):
        """Test model loading when file doesn't exist"""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            load_model('nonexistent_model')

if __name__ == "__main__":
    pytest.main([__file__])