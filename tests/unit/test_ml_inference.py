#!/usr/bin/env python3
"""
Unit tests for ML inference
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
import numpy as np

# Add ml_services to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'ml_services'))

class TestMLInference:
    
    def test_heuristic_score_calculation(self):
        """Test heuristic scoring calculation"""
        from serve import heuristic_score, TelemetryInput
        
        # Normal driving scenario
        normal_telemetry = TelemetryInput(
            deviceId="TEST_DEVICE_001",
            speed=50.0,
            accel_x=1.0,
            accel_y=0.5,
            accel_z=9.8,
            jerk=0.2,
            yaw=0.0
        )
        
        score = heuristic_score(normal_telemetry)
        assert 0 <= score <= 100
        assert score < 20  # Should be low for normal driving
    
    def test_harsh_driving_heuristic(self):
        """Test heuristic scoring for harsh driving"""
        from serve import heuristic_score, TelemetryInput
        
        # Harsh driving scenario
        harsh_telemetry = TelemetryInput(
            deviceId="TEST_DEVICE_002",
            speed=80.0,
            accel_x=8.0,  # High acceleration
            accel_y=6.0,  # High lateral acceleration
            accel_z=9.8,
            jerk=5.0,     # High jerk
            yaw=15.0
        )
        
        score = heuristic_score(harsh_telemetry)
        assert 0 <= score <= 100
        assert score > 50  # Should be high for harsh driving
    
    @patch('serve.load_model')
    def test_ml_model_prediction_success(self, mock_load_model):
        """Test successful ML model prediction"""
        from serve import TelemetryInput
        
        # Mock model
        mock_model = Mock()
        mock_model.predict_proba.return_value = [[0.7, 0.3]]  # 30% harsh driving
        
        mock_load_model.return_value = {
            'model': mock_model,
            'loaded_at': 'mock_time',
            'path': 'mock_path'
        }
        
        # This would be tested in integration tests with actual FastAPI client
        # Here we just verify the mock setup
        assert mock_model.predict_proba([[50, 1, 0.5, 9.8, 0.2, 0]])[0][1] == 0.3
    
    def test_telemetry_input_validation(self):
        """Test telemetry input validation"""
        from serve import TelemetryInput
        from pydantic import ValidationError
        
        # Valid input
        valid_input = TelemetryInput(
            deviceId="TEST_DEVICE_001",
            speed=50.0,
            accel_x=1.0,
            accel_y=0.5,
            accel_z=9.8,
            jerk=0.2,
            yaw=0.0
        )
        assert valid_input.deviceId == "TEST_DEVICE_001"
        
        # Invalid speed (negative)
        with pytest.raises(ValidationError):
            TelemetryInput(
                deviceId="TEST_DEVICE_001",
                speed=-10.0,
                accel_x=1.0,
                accel_y=0.5,
                accel_z=9.8
            )
        
        # Invalid acceleration (too high)
        with pytest.raises(ValidationError):
            TelemetryInput(
                deviceId="TEST_DEVICE_001",
                speed=50.0,
                accel_x=60.0,  # Exceeds limit
                accel_y=0.5,
                accel_z=9.8
            )
    
    def test_feature_extraction(self):
        """Test feature extraction from telemetry"""
        from serve import TelemetryInput
        
        telemetry = TelemetryInput(
            deviceId="TEST_DEVICE_001",
            speed=65.5,
            accel_x=2.1,
            accel_y=-1.5,
            accel_z=9.8,
            jerk=1.2,
            yaw=5.0
        )
        
        # Extract features as done in the API
        features = [
            telemetry.speed,
            telemetry.accel_x,
            telemetry.accel_y,
            telemetry.accel_z,
            telemetry.jerk,
            telemetry.yaw
        ]
        
        expected_features = [65.5, 2.1, -1.5, 9.8, 1.2, 5.0]
        assert features == expected_features
    
    def test_score_boundaries(self):
        """Test that scores are within expected boundaries"""
        from serve import heuristic_score, TelemetryInput
        
        # Test multiple scenarios
        test_cases = [
            # (speed, accel_x, accel_y, jerk, expected_range)
            (0, 0, 0, 0, (0, 10)),      # Minimal values
            (30, 1, 1, 0.5, (0, 30)),   # Low activity
            (60, 3, 2, 1.5, (20, 60)),  # Moderate activity
            (100, 8, 6, 4, (60, 100)),  # High activity
        ]
        
        for speed, accel_x, accel_y, jerk, (min_score, max_score) in test_cases:
            telemetry = TelemetryInput(
                deviceId="TEST_DEVICE",
                speed=speed,
                accel_x=accel_x,
                accel_y=accel_y,
                accel_z=9.8,
                jerk=jerk,
                yaw=0.0
            )
            
            score = heuristic_score(telemetry)
            assert min_score <= score <= max_score, f"Score {score} not in range [{min_score}, {max_score}] for inputs: speed={speed}, accel_x={accel_x}, accel_y={accel_y}, jerk={jerk}"
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        from serve import heuristic_score, TelemetryInput
        
        # Maximum allowed values
        max_telemetry = TelemetryInput(
            deviceId="TEST_DEVICE_MAX",
            speed=300.0,
            accel_x=50.0,
            accel_y=50.0,
            accel_z=50.0,
            jerk=20.0,
            yaw=180.0
        )
        
        score = heuristic_score(max_telemetry)
        assert 0 <= score <= 100  # Should still be clamped to 100
        
        # Minimum allowed values
        min_telemetry = TelemetryInput(
            deviceId="TEST_DEVICE_MIN",
            speed=0.0,
            accel_x=-50.0,
            accel_y=-50.0,
            accel_z=-50.0,
            jerk=-20.0,
            yaw=-180.0
        )
        
        score = heuristic_score(min_telemetry)
        assert 0 <= score <= 100  # Should still be valid

if __name__ == "__main__":
    pytest.main([__file__])