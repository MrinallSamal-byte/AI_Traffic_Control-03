import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_services.driver_score import predict_score, heuristic_score

def test_predict_score_returns_valid_range():
    """Test that predict_score returns score in valid range 0-100"""
    telemetry = {
        "speed": 50.0,
        "accel_x": 1.2,
        "accel_y": 0.3,
        "accel_z": 9.8,
        "jerk": 0.5,
        "yaw": 0.02
    }
    
    result = predict_score(telemetry)
    
    assert isinstance(result, dict)
    assert "score" in result
    assert "model" in result
    assert 0 <= result["score"] <= 100
    assert result["model"] in ["random_forest", "heuristic"]

def test_predict_score_with_missing_fields():
    """Test predict_score handles missing telemetry fields gracefully"""
    telemetry = {
        "speed": 30.0,
        "accel_x": 0.5
        # Missing other fields
    }
    
    result = predict_score(telemetry)
    
    assert isinstance(result, dict)
    assert "score" in result
    assert "model" in result
    assert 0 <= result["score"] <= 100

def test_heuristic_score_calculation():
    """Test heuristic score calculation"""
    telemetry = {
        "speed": 60.0,
        "accel_x": 2.0,
        "accel_y": 1.0,
        "jerk": 1.5
    }
    
    score = heuristic_score(telemetry)
    
    assert isinstance(score, float)
    assert 0 <= score <= 100

def test_high_risk_scenario():
    """Test high-risk driving scenario produces higher score"""
    high_risk_telemetry = {
        "speed": 120.0,  # High speed
        "accel_x": 8.0,  # Harsh acceleration
        "accel_y": 3.0,  # High lateral acceleration
        "accel_z": 9.8,
        "jerk": 5.0,     # High jerk
        "yaw": 0.5       # High yaw rate
    }
    
    low_risk_telemetry = {
        "speed": 30.0,   # Low speed
        "accel_x": 0.1,  # Gentle acceleration
        "accel_y": 0.1,  # Low lateral acceleration
        "accel_z": 9.8,
        "jerk": 0.1,     # Low jerk
        "yaw": 0.01      # Low yaw rate
    }
    
    high_risk_score = predict_score(high_risk_telemetry)["score"]
    low_risk_score = predict_score(low_risk_telemetry)["score"]
    
    assert high_risk_score > low_risk_score

def test_predict_score_consistency():
    """Test that predict_score returns consistent results for same input"""
    telemetry = {
        "speed": 45.0,
        "accel_x": 1.0,
        "accel_y": 0.5,
        "accel_z": 9.8,
        "jerk": 0.3,
        "yaw": 0.05
    }
    
    result1 = predict_score(telemetry)
    result2 = predict_score(telemetry)
    
    # Should be consistent (allowing for small floating point differences)
    assert abs(result1["score"] - result2["score"]) < 0.01
    assert result1["model"] == result2["model"]