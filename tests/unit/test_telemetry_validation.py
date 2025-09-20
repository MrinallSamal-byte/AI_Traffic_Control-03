#!/usr/bin/env python3
"""
Unit tests for telemetry validation
"""

import pytest
import json
from datetime import datetime
from pydantic import ValidationError
import sys
import os

# Add stream_processor to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'stream_processor'))
from schemas import TelemetryModel, AccelerationModel, LocationModel

class TestTelemetryValidation:
    
    def test_valid_telemetry_message(self):
        """Test validation of a valid telemetry message"""
        valid_message = {
            "deviceId": "DEVICE_12345678",
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {
                "lat": 20.2961,
                "lon": 85.8245,
                "altitude": 100.5
            },
            "speedKmph": 65.5,
            "acceleration": {
                "x": 2.1,
                "y": -1.5,
                "z": 9.8
            },
            "fuelLevel": 75.5,
            "heading": 180.0
        }
        
        # Should not raise any exception
        telemetry = TelemetryModel(**valid_message)
        assert telemetry.deviceId == "DEVICE_12345678"
        assert telemetry.speedKmph == 65.5
        assert telemetry.fuelLevel == 75.5
        assert telemetry.acceleration.x == 2.1
    
    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing"""
        
        # Missing deviceId
        with pytest.raises(ValidationError) as exc_info:
            TelemetryModel(**{
                "timestamp": "2024-01-15T10:30:00Z",
                "location": {"lat": 20.2961, "lon": 85.8245},
                "speedKmph": 65.5,
                "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
                "fuelLevel": 75.5
            })
        assert "deviceId" in str(exc_info.value)
        
        # Missing acceleration
        with pytest.raises(ValidationError) as exc_info:
            TelemetryModel(**{
                "deviceId": "DEVICE_12345678",
                "timestamp": "2024-01-15T10:30:00Z",
                "location": {"lat": 20.2961, "lon": 85.8245},
                "speedKmph": 65.5,
                "fuelLevel": 75.5
            })
        assert "acceleration" in str(exc_info.value)
        
        # Missing fuelLevel
        with pytest.raises(ValidationError) as exc_info:
            TelemetryModel(**{
                "deviceId": "DEVICE_12345678",
                "timestamp": "2024-01-15T10:30:00Z",
                "location": {"lat": 20.2961, "lon": 85.8245},
                "speedKmph": 65.5,
                "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8}
            })
        assert "fuelLevel" in str(exc_info.value)
    
    def test_invalid_device_id_format(self):
        """Test validation fails for invalid deviceId format"""
        invalid_messages = [
            {"deviceId": "short"},  # Too short
            {"deviceId": "device-with-dashes"},  # Invalid characters
            {"deviceId": "lowercase_device_id"},  # Lowercase not allowed
            {"deviceId": "A" * 33},  # Too long
        ]
        
        base_message = {
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {"lat": 20.2961, "lon": 85.8245},
            "speedKmph": 65.5,
            "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
            "fuelLevel": 75.5
        }
        
        for invalid_msg in invalid_messages:
            with pytest.raises(ValidationError):
                TelemetryModel(**{**base_message, **invalid_msg})
    
    def test_invalid_location_coordinates(self):
        """Test validation fails for invalid coordinates"""
        base_message = {
            "deviceId": "DEVICE_12345678",
            "timestamp": "2024-01-15T10:30:00Z",
            "speedKmph": 65.5,
            "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
            "fuelLevel": 75.5
        }
        
        # Invalid latitude (> 90)
        with pytest.raises(ValidationError):
            TelemetryModel(**{
                **base_message,
                "location": {"lat": 95.0, "lon": 85.8245}
            })
        
        # Invalid longitude (< -180)
        with pytest.raises(ValidationError):
            TelemetryModel(**{
                **base_message,
                "location": {"lat": 20.2961, "lon": -185.0}
            })
    
    def test_invalid_speed_values(self):
        """Test validation fails for invalid speed values"""
        base_message = {
            "deviceId": "DEVICE_12345678",
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {"lat": 20.2961, "lon": 85.8245},
            "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
            "fuelLevel": 75.5
        }
        
        # Negative speed
        with pytest.raises(ValidationError):
            TelemetryModel(**{**base_message, "speedKmph": -10.0})
        
        # Speed too high
        with pytest.raises(ValidationError):
            TelemetryModel(**{**base_message, "speedKmph": 350.0})
    
    def test_invalid_acceleration_values(self):
        """Test validation fails for extreme acceleration values"""
        base_message = {
            "deviceId": "DEVICE_12345678",
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {"lat": 20.2961, "lon": 85.8245},
            "speedKmph": 65.5,
            "fuelLevel": 75.5
        }
        
        # Acceleration too high
        with pytest.raises(ValidationError):
            TelemetryModel(**{
                **base_message,
                "acceleration": {"x": 60.0, "y": -1.5, "z": 9.8}
            })
        
        # Acceleration too low
        with pytest.raises(ValidationError):
            TelemetryModel(**{
                **base_message,
                "acceleration": {"x": 2.1, "y": -60.0, "z": 9.8}
            })
    
    def test_invalid_fuel_level(self):
        """Test validation fails for invalid fuel level values"""
        base_message = {
            "deviceId": "DEVICE_12345678",
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {"lat": 20.2961, "lon": 85.8245},
            "speedKmph": 65.5,
            "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8}
        }
        
        # Negative fuel level
        with pytest.raises(ValidationError):
            TelemetryModel(**{**base_message, "fuelLevel": -5.0})
        
        # Fuel level > 100%
        with pytest.raises(ValidationError):
            TelemetryModel(**{**base_message, "fuelLevel": 105.0})
    
    def test_invalid_timestamp_format(self):
        """Test validation fails for invalid timestamp format"""
        base_message = {
            "deviceId": "DEVICE_12345678",
            "location": {"lat": 20.2961, "lon": 85.8245},
            "speedKmph": 65.5,
            "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
            "fuelLevel": 75.5
        }
        
        invalid_timestamps = [
            "2024-01-15 10:30:00",  # Missing timezone
            "invalid-timestamp",
            "2024-13-01T10:30:00Z",  # Invalid month
            ""
        ]
        
        for invalid_ts in invalid_timestamps:
            with pytest.raises(ValidationError):
                TelemetryModel(**{**base_message, "timestamp": invalid_ts})
    
    def test_optional_fields_validation(self):
        """Test validation of optional fields when provided"""
        valid_message = {
            "deviceId": "DEVICE_12345678",
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {"lat": 20.2961, "lon": 85.8245},
            "speedKmph": 65.5,
            "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
            "fuelLevel": 75.5,
            "heading": 180.0,
            "engineData": {
                "rpm": 2500.0,
                "engineTemp": 85.0
            },
            "diagnostics": {
                "errorCodes": ["P0001", "P0002"],
                "batteryVoltage": 12.6
            }
        }
        
        # Should validate successfully
        telemetry = TelemetryModel(**valid_message)
        assert telemetry.heading == 180.0
        assert telemetry.engineData.rpm == 2500.0
        assert len(telemetry.diagnostics.errorCodes) == 2
    
    def test_boundary_values(self):
        """Test validation at boundary values"""
        # Test minimum valid values
        min_valid = {
            "deviceId": "A1234567",  # 8 chars minimum
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {"lat": -90.0, "lon": -180.0},
            "speedKmph": 0.0,
            "acceleration": {"x": -50.0, "y": -50.0, "z": -50.0},
            "fuelLevel": 0.0
        }
        telemetry = TelemetryModel(**min_valid)
        assert telemetry.speedKmph == 0.0
        
        # Test maximum valid values
        max_valid = {
            "deviceId": "A" * 32,  # 32 chars maximum
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {"lat": 90.0, "lon": 180.0},
            "speedKmph": 300.0,
            "acceleration": {"x": 50.0, "y": 50.0, "z": 50.0},
            "fuelLevel": 100.0,
            "heading": 360.0
        }
        telemetry = TelemetryModel(**max_valid)
        assert telemetry.speedKmph == 300.0
        assert telemetry.heading == 360.0

if __name__ == "__main__":
    pytest.main([__file__])