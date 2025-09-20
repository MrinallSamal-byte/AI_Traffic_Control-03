#!/usr/bin/env python3
"""
Unit tests for ML inference functionality
"""

import pytest
import numpy as np
import sys
import os
from unittest.mock import Mock, patch
import joblib
import json
from pathlib import Path

# Add ml_services to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_services.driver_score import predict_score, heuristic_score

class TestMLInference:
    """Test ML inference functionality"""
    
    def test_heuristic_score_calculation(self):
        """Test heuristic scoring algorithm"""
        # Test normal driving
        normal_telemetry = {
            "speed": 50.0,
            "accel_x": 0.5,
            "accel_y": 0.2,
            "jerk": 1.0
        }
        
        score = heuristic_score(normal_telemetry)
        assert 0 <= score <= 100
        assert score < 30  # Should be low risk
        
        # Test aggressive driving
        aggressive_telemetry = {
            "speed": 100.0,
            "accel_x": 5.0,
            "accel_y": 3.0,
            "jerk": 8.0
        }
        
        score = heuristic_score(aggressive_telemetry)
        assert 0 <= score <= 100
        assert score > 50  # Should be high risk
    
    def test_predict_score_with_model(self):
        """Test prediction with loaded model"""
        # Mock model
        mock_model = Mock()
        mock_model.predict.return_value = [65.5]
        
        with patch('ml_services.driver_score._load_model', return_value=mock_model):
            telemetry = {
                "speed": 60.0,
                "accel_x": 1.5,
                "accel_y": -0.8,
                "accel_z": 9.8,
                "jerk": 2.0,
                "yaw": 10.0
            }
            
            result = predict_score(telemetry)
            
            assert result["score"] == 65.5
            assert result["model"] == "random_forest"
            mock_model.predict.assert_called_once()
    
    def test_predict_score_fallback_to_heuristic(self):
        """Test fallback to heuristic when model fails"""
        with patch('ml_services.driver_score._load_model', return_value=None):
            telemetry = {
                "speed": 45.0,
                "accel_x": 0.8,
                "accel_y": 0.3,
                "jerk": 1.5
            }
            
            result = predict_score(telemetry)
            
            assert "score" in result
            assert result["model"] == "heuristic"
            assert 0 <= result["score"] <= 100
    
    def test_predict_score_with_missing_fields(self):
        """Test prediction with missing telemetry fields"""
        incomplete_telemetry = {
            "speed": 50.0
            # Missing other fields
        }
        
        result = predict_score(incomplete_telemetry)
        
        # Should handle missing fields gracefully
        assert "score" in result
        assert 0 <= result["score"] <= 100
    
    def test_predict_score_with_invalid_values(self):
        """Test prediction with invalid values"""
        invalid_telemetry = {
            "speed": "invalid",
            "accel_x": None,
            "accel_y": "not_a_number"
        }
        
        result = predict_score(invalid_telemetry)
        
        # Should handle invalid values gracefully
        assert "score" in result
        assert 0 <= result["score"] <= 100
    
    def test_score_boundary_conditions(self):
        """Test score calculation at boundary conditions"""
        # Test zero values
        zero_telemetry = {
            "speed": 0.0,
            "accel_x": 0.0,
            "accel_y": 0.0,
            "jerk": 0.0
        }
        
        score = heuristic_score(zero_telemetry)
        assert score == 0.0
        
        # Test extreme values
        extreme_telemetry = {
            "speed": 200.0,
            "accel_x": 10.0,
            "accel_y": 10.0,
            "jerk": 15.0
        }
        
        score = heuristic_score(extreme_telemetry)
        assert score == 100.0  # Should be clamped to max
    
    def test_model_loading_error_handling(self):
        """Test model loading error handling"""
        with patch('ml_services.driver_score.joblib.load', side_effect=Exception("Load error")):
            with patch('ml_services.driver_score.os.path.exists', return_value=True):
                telemetry = {"speed": 50.0, "accel_x": 1.0}
                result = predict_score(telemetry)
                
                # Should fallback to heuristic
                assert result["model"] == "heuristic"
    
    @pytest.mark.parametrize("speed,accel_x,accel_y,jerk,expected_range", [
        (30.0, 0.5, 0.2, 1.0, (0, 20)),      # Low risk
        (60.0, 2.0, 1.0, 3.0, (20, 60)),     # Medium risk
        (100.0, 5.0, 4.0, 8.0, (60, 100)),   # High risk
    ])
    def test_risk_level_classification(self, speed, accel_x, accel_y, jerk, expected_range):
        """Test risk level classification"""
        telemetry = {
            "speed": speed,
            "accel_x": accel_x,
            "accel_y": accel_y,
            "jerk": jerk
        }
        
        score = heuristic_score(telemetry)
        assert expected_range[0] <= score <= expected_range[1]

class TestModelManager:
    """Test model management functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        # Import here to avoid circular imports
        from ml_services.ml_api import ModelManager
        self.ModelManager = ModelManager
    
    def test_model_manager_initialization(self):
        """Test ModelManager initialization"""
        with patch.object(self.ModelManager, 'load_latest_model'):
            manager = self.ModelManager()
            assert manager.current_model is None
            assert manager.model_version is None
            assert manager.model_metadata == {}
    
    def test_heuristic_prediction_fallback(self):
        """Test heuristic prediction fallback"""
        manager = self.ModelManager()
        manager.current_model = None  # Force heuristic
        
        features = [50.0, 1.0, 0.5, 9.8, 2.0, 10.0]
        result = manager.predict(features)
        
        assert result["model"] == "heuristic"
        assert "score" in result
        assert "confidence" in result
        assert result["confidence"] == 0.6
    
    def test_model_prediction_success(self):
        """Test successful model prediction"""
        manager = self.ModelManager()
        
        # Mock model
        mock_model = Mock()
        mock_model.predict.return_value = [75.5]
        manager.current_model = mock_model
        manager.model_version = "test_v1"
        
        features = [60.0, 2.0, 1.0, 9.8, 3.0, 15.0]
        result = manager.predict(features)
        
        assert result["score"] == 75.5
        assert result["model"] == "test_v1"
        assert result["confidence"] == 0.85
    
    def test_model_prediction_error_fallback(self):
        """Test fallback when model prediction fails"""
        manager = self.ModelManager()
        
        # Mock model that raises exception
        mock_model = Mock()
        mock_model.predict.side_effect = Exception("Prediction error")
        manager.current_model = mock_model
        
        features = [50.0, 1.0, 0.5, 9.8, 2.0, 10.0]
        result = manager.predict(features)
        
        # Should fallback to heuristic
        assert result["model"] == "heuristic"
        assert "score" in result
    
    def test_model_save_functionality(self):
        """Test model saving with metadata"""
        manager = self.ModelManager()
        
        # Mock model
        mock_model = Mock()
        metadata = {
            "version": "test_v1",
            "created_at": "2024-01-01T00:00:00Z",
            "performance": {"mse": 10.5, "r2": 0.85}
        }
        
        with patch('ml_services.ml_api.joblib.dump') as mock_dump:
            with patch('builtins.open', create=True) as mock_open:
                with patch('json.dump') as mock_json_dump:
                    result = manager.save_model(mock_model, "test_v1", metadata)
                    
                    assert result is True
                    mock_dump.assert_called_once()
                    mock_json_dump.assert_called_once_with(metadata, mock_open().__enter__(), indent=2)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])