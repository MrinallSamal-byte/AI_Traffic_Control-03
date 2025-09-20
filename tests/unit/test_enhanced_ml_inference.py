#!/usr/bin/env python3
"""
Unit tests for enhanced ML inference system
"""

import pytest
import json
import sys
import os
import tempfile
import joblib
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Add ml_services to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'ml_services'))
from enhanced_ml_api import (
    TelemetryInput, PredictionResponse, BatchTelemetryInput,
    load_model, prepare_features, get_risk_level, heuristic_prediction
)

class TestEnhancedMLInference:
    
    @pytest.fixture
    def sample_telemetry(self):
        """Sample telemetry data for testing"""
        return TelemetryInput(
            deviceId="DEVICE_12345678",
            speed=65.5,
            accel_x=2.1,
            accel_y=-1.5,
            accel_z=9.8,
            jerk=1.2,
            yaw_rate=5.0,
            heading_change=2.0,
            throttle_position=45.0,
            brake_position=0.0,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    @pytest.fixture
    def mock_model_bundle(self):
        """Create a mock model bundle for testing"""
        # Create simple mock model
        model = Mock(spec=RandomForestClassifier)
        model.predict_proba.return_value = np.array([[0.3, 0.7]])  # 70% harsh driving probability
        
        scaler = Mock(spec=StandardScaler)
        scaler.transform.return_value = np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0]])
        
        return {
            'model': model,
            'scaler': scaler,
            'feature_names': [
                'speed_kmph', 'accel_x', 'accel_y', 'accel_z', 'jerk', 'yaw_rate',
                'heading_change', 'throttle_position', 'brake_position',
                'accel_magnitude', 'lateral_accel', 'speed_accel_ratio', 'brake_accel_correlation'
            ],
            'metadata': {
                'model_version': 'test_v1.0',
                'model_type': 'RandomForestClassifier',
                'test_accuracy': 0.85,
                'auc_score': 0.92
            }
        }
    
    def test_telemetry_input_validation(self):
        """Test telemetry input validation"""
        # Valid input
        valid_telemetry = TelemetryInput(
            deviceId="DEVICE_12345678",
            speed=65.5,
            accel_x=2.1,
            accel_y=-1.5,
            accel_z=9.8
        )
        assert valid_telemetry.deviceId == "DEVICE_12345678"
        assert valid_telemetry.speed == 65.5
        
        # Invalid device ID
        with pytest.raises(ValueError):
            TelemetryInput(
                deviceId="short",  # Too short
                speed=65.5,
                accel_x=2.1,
                accel_y=-1.5,
                accel_z=9.8
            )
        
        # Invalid speed (negative)
        with pytest.raises(ValueError):
            TelemetryInput(
                deviceId="DEVICE_12345678",
                speed=-10.0,
                accel_x=2.1,
                accel_y=-1.5,
                accel_z=9.8
            )
        
        # Invalid acceleration (out of range)
        with pytest.raises(ValueError):
            TelemetryInput(
                deviceId="DEVICE_12345678",
                speed=65.5,
                accel_x=60.0,  # Too high
                accel_y=-1.5,
                accel_z=9.8
            )
    
    def test_prepare_features(self, sample_telemetry):
        """Test feature preparation from telemetry"""
        features = prepare_features(sample_telemetry)
        
        # Check shape
        assert features.shape == (1, 13)  # 9 base + 4 derived features
        
        # Check base features
        assert features[0, 0] == sample_telemetry.speed
        assert features[0, 1] == sample_telemetry.accel_x
        assert features[0, 2] == sample_telemetry.accel_y
        assert features[0, 3] == sample_telemetry.accel_z
        
        # Check derived features are calculated
        accel_magnitude = np.sqrt(
            sample_telemetry.accel_x**2 + 
            sample_telemetry.accel_y**2 + 
            sample_telemetry.accel_z**2
        )
        assert abs(features[0, 9] - accel_magnitude) < 1e-6
        
        lateral_accel = np.sqrt(sample_telemetry.accel_x**2 + sample_telemetry.accel_y**2)
        assert abs(features[0, 10] - lateral_accel) < 1e-6
    
    def test_get_risk_level(self):
        """Test risk level categorization"""
        assert get_risk_level(85.0) == "HIGH"
        assert get_risk_level(70.0) == "MEDIUM"
        assert get_risk_level(50.0) == "LOW"
        assert get_risk_level(30.0) == "MINIMAL"
        
        # Boundary cases
        assert get_risk_level(80.0) == "HIGH"
        assert get_risk_level(79.9) == "MEDIUM"
        assert get_risk_level(60.0) == "MEDIUM"
        assert get_risk_level(59.9) == "LOW"
        assert get_risk_level(40.0) == "LOW"
        assert get_risk_level(39.9) == "MINIMAL"
    
    def test_heuristic_prediction(self, sample_telemetry):
        """Test heuristic fallback prediction"""
        result = heuristic_prediction(sample_telemetry)
        
        assert 'prediction' in result
        assert 'confidence' in result
        assert 'model_type' in result
        assert 'model_version' in result
        assert 'warnings' in result
        
        assert result['model_type'] == 'heuristic'
        assert result['model_version'] == 'heuristic_v1.0'
        assert result['confidence'] is None
        assert 0.0 <= result['prediction'] <= 100.0
        assert len(result['warnings']) > 0
    
    def test_heuristic_prediction_edge_cases(self):
        """Test heuristic prediction with edge case values"""
        # High risk scenario
        high_risk_telemetry = TelemetryInput(
            deviceId="DEVICE_12345678",
            speed=120.0,  # High speed
            accel_x=15.0,  # Hard braking
            accel_y=10.0,  # Sharp turn
            accel_z=9.8,
            jerk=8.0,  # High jerk
            brake_position=90.0  # Hard braking
        )
        
        result = heuristic_prediction(high_risk_telemetry)
        assert result['prediction'] > 50.0  # Should be high risk
        
        # Low risk scenario
        low_risk_telemetry = TelemetryInput(
            deviceId="DEVICE_12345678",
            speed=30.0,  # Low speed
            accel_x=0.5,  # Gentle acceleration
            accel_y=0.2,
            accel_z=9.8,
            jerk=0.1,  # Low jerk
            brake_position=5.0  # Light braking
        )
        
        result = heuristic_prediction(low_risk_telemetry)
        assert result['prediction'] < 30.0  # Should be low risk
    
    @patch('joblib.load')
    @patch('os.path.exists')
    def test_load_model_success(self, mock_exists, mock_joblib_load, mock_model_bundle):
        """Test successful model loading"""
        mock_exists.return_value = True
        mock_joblib_load.return_value = mock_model_bundle
        
        model_info = load_model('test_model')
        
        assert 'model' in model_info
        assert 'scaler' in model_info
        assert 'feature_names' in model_info
        assert 'metadata' in model_info
        assert 'loaded_at' in model_info
        assert 'load_time' in model_info
        
        assert model_info['metadata']['model_version'] == 'test_v1.0'
        assert len(model_info['feature_names']) == 13
    
    @patch('os.path.exists')
    def test_load_model_file_not_found(self, mock_exists):
        """Test model loading when file doesn't exist"""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            load_model('nonexistent_model')
    
    @patch('joblib.load')
    @patch('os.path.exists')
    def test_load_model_legacy_format(self, mock_exists, mock_joblib_load):
        """Test loading model in legacy format (not a dict)"""
        mock_exists.return_value = True
        mock_model = Mock(spec=RandomForestClassifier)
        mock_joblib_load.return_value = mock_model  # Not a dict
        
        model_info = load_model('legacy_model')
        
        assert model_info['model'] == mock_model
        assert model_info['scaler'] is None
        assert model_info['feature_names'] == []
        assert model_info['metadata'] == {}
    
    def test_batch_telemetry_input_validation(self, sample_telemetry):
        """Test batch telemetry input validation"""
        # Valid batch
        batch_input = BatchTelemetryInput(
            telemetry_data=[sample_telemetry, sample_telemetry],
            batch_id="test_batch_123"
        )
        assert len(batch_input.telemetry_data) == 2
        assert batch_input.batch_id == "test_batch_123"
        
        # Too many items (over limit of 100)
        large_batch = [sample_telemetry] * 101
        with pytest.raises(ValueError):
            BatchTelemetryInput(telemetry_data=large_batch)
    
    def test_prediction_response_model(self):
        """Test prediction response model"""
        response = PredictionResponse(
            deviceId="DEVICE_12345678",
            prediction=75.5,
            confidence=0.85,
            model_version="test_v1.0",
            model_type="RandomForestClassifier",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            processing_time_ms=25.5,
            risk_level="MEDIUM",
            features_used=["speed", "accel_x", "accel_y"],
            warnings=["Test warning"]
        )
        
        assert response.deviceId == "DEVICE_12345678"
        assert response.prediction == 75.5
        assert response.risk_level == "MEDIUM"
        assert len(response.features_used) == 3
        assert len(response.warnings) == 1
    
    def test_device_id_validation_edge_cases(self):
        """Test device ID validation with various edge cases"""
        valid_device_ids = [
            "DEVICE_12345678",
            "DEV_ABC123XYZ",
            "VEHICLE-001",
            "A1B2C3D4E5F6G7H8",
            "12345678"
        ]
        
        for device_id in valid_device_ids:
            telemetry = TelemetryInput(
                deviceId=device_id,
                speed=50.0,
                accel_x=1.0,
                accel_y=1.0,
                accel_z=9.8
            )
            assert telemetry.deviceId == device_id
        
        invalid_device_ids = [
            "short",  # Too short
            "A" * 33,  # Too long
            "DEVICE@123",  # Invalid character
            "device with spaces",  # Spaces not allowed
            "",  # Empty
        ]
        
        for device_id in invalid_device_ids:
            with pytest.raises(ValueError):
                TelemetryInput(
                    deviceId=device_id,
                    speed=50.0,
                    accel_x=1.0,
                    accel_y=1.0,
                    accel_z=9.8
                )
    
    def test_feature_calculation_accuracy(self):
        """Test accuracy of derived feature calculations"""
        telemetry = TelemetryInput(
            deviceId="DEVICE_12345678",
            speed=60.0,
            accel_x=3.0,
            accel_y=4.0,
            accel_z=9.8,
            jerk=2.0,
            yaw_rate=10.0,
            heading_change=5.0,
            throttle_position=50.0,
            brake_position=10.0
        )
        
        features = prepare_features(telemetry)
        
        # Manually calculate expected derived features
        expected_accel_magnitude = np.sqrt(3.0**2 + 4.0**2 + 9.8**2)
        expected_lateral_accel = np.sqrt(3.0**2 + 4.0**2)
        expected_speed_accel_ratio = 60.0 / (expected_accel_magnitude + 1e-6)
        expected_brake_accel_correlation = 10.0 * abs(3.0)
        
        # Check calculated features
        assert abs(features[0, 9] - expected_accel_magnitude) < 1e-6
        assert abs(features[0, 10] - expected_lateral_accel) < 1e-6
        assert abs(features[0, 11] - expected_speed_accel_ratio) < 1e-6
        assert abs(features[0, 12] - expected_brake_accel_correlation) < 1e-6
    
    def test_extreme_values_handling(self):
        """Test handling of extreme but valid values"""
        # Maximum valid values
        max_telemetry = TelemetryInput(
            deviceId="DEVICE_12345678",
            speed=300.0,  # Max speed
            accel_x=50.0,  # Max acceleration
            accel_y=50.0,
            accel_z=50.0,
            jerk=20.0,  # Max jerk
            yaw_rate=180.0,  # Max yaw rate
            heading_change=180.0,
            throttle_position=100.0,
            brake_position=100.0
        )
        
        features = prepare_features(max_telemetry)
        assert features.shape == (1, 13)
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))
        
        # Minimum valid values
        min_telemetry = TelemetryInput(
            deviceId="DEVICE_12345678",
            speed=0.0,
            accel_x=-50.0,
            accel_y=-50.0,
            accel_z=-50.0,
            jerk=-20.0,
            yaw_rate=-180.0,
            heading_change=-180.0,
            throttle_position=0.0,
            brake_position=0.0
        )
        
        features = prepare_features(min_telemetry)
        assert features.shape == (1, 13)
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))
    
    def test_zero_division_protection(self):
        """Test protection against zero division in feature calculations"""
        # Zero acceleration scenario
        zero_accel_telemetry = TelemetryInput(
            deviceId="DEVICE_12345678",
            speed=60.0,
            accel_x=0.0,
            accel_y=0.0,
            accel_z=0.0,  # All zero acceleration
            jerk=0.0,
            yaw_rate=0.0,
            heading_change=0.0,
            throttle_position=0.0,
            brake_position=0.0
        )
        
        features = prepare_features(zero_accel_telemetry)
        
        # Check that speed_accel_ratio doesn't cause division by zero
        # Should use 1e-6 as minimum denominator
        expected_ratio = 60.0 / 1e-6
        assert abs(features[0, 11] - expected_ratio) < 1e-3
        
        # Check no NaN or Inf values
        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))

if __name__ == "__main__":
    pytest.main([__file__, "-v"])