#!/usr/bin/env python3
"""
Unit tests for enhanced telemetry validation with DLQ and enrichment
"""

import pytest
import json
import sys
import os
from datetime import datetime, timedelta

# Add stream_processor to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'stream_processor'))
from enhanced_validator import EnhancedTelemetryValidator, ValidationResult, create_dlq_message

class TestEnhancedTelemetryValidation:
    
    @pytest.fixture
    def validator(self):
        """Create validator instance for testing"""
        return EnhancedTelemetryValidator()
    
    @pytest.fixture
    def valid_telemetry(self):
        """Valid telemetry message for testing"""
        return {
            "deviceId": "DEVICE_12345678",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "location": {"lat": 20.2961, "lon": 85.8245},
            "speedKmph": 65.5,
            "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
            "fuelLevel": 75.5,
            "heading": 180.0
        }
    
    def test_valid_telemetry_validation(self, validator, valid_telemetry):
        """Test validation of valid telemetry message"""
        result = validator.validate_and_enrich(valid_telemetry)
        
        assert result.is_valid is True
        assert result.enriched_data is not None
        assert result.errors is None or len(result.errors) == 0
        
        # Check enrichment
        enriched = result.enriched_data
        assert 'processed_at' in enriched
        assert 'validator_version' in enriched
        assert 'acceleration_magnitude' in enriched
        assert 'road_segment' in enriched
    
    def test_invalid_device_id(self, validator, valid_telemetry):
        """Test validation fails for invalid device ID"""
        invalid_telemetry = valid_telemetry.copy()
        invalid_telemetry['deviceId'] = 'invalid'
        
        result = validator.validate_and_enrich(invalid_telemetry)
        
        assert result.is_valid is False
        assert result.errors is not None
        assert len(result.errors) > 0
        assert any('Schema validation failed' in error for error in result.errors)
    
    def test_missing_required_fields(self, validator):
        """Test validation fails when required fields are missing"""
        incomplete_telemetry = {
            "deviceId": "DEVICE_12345678",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
            # Missing location, speedKmph, acceleration
        }
        
        result = validator.validate_and_enrich(incomplete_telemetry)
        
        assert result.is_valid is False
        assert result.errors is not None
        assert any('Schema validation failed' in error for error in result.errors)
    
    def test_invalid_coordinates(self, validator, valid_telemetry):
        """Test validation fails for invalid GPS coordinates"""
        invalid_telemetry = valid_telemetry.copy()
        invalid_telemetry['location'] = {"lat": 95.0, "lon": 185.0}  # Out of range
        
        result = validator.validate_and_enrich(invalid_telemetry)
        
        assert result.is_valid is False
        assert result.errors is not None
    
    def test_business_rule_validation(self, validator, valid_telemetry):
        """Test business rule validation"""
        # Test unrealistic acceleration
        invalid_telemetry = valid_telemetry.copy()
        invalid_telemetry['acceleration'] = {"x": 25.0, "y": 25.0, "z": 25.0}  # Very high
        
        result = validator.validate_and_enrich(invalid_telemetry)
        
        assert result.is_valid is False
        assert result.errors is not None
        assert any('Unrealistic acceleration' in error for error in result.errors)
    
    def test_future_timestamp_validation(self, validator, valid_telemetry):
        """Test validation fails for timestamps too far in future"""
        future_time = datetime.utcnow() + timedelta(hours=1)
        invalid_telemetry = valid_telemetry.copy()
        invalid_telemetry['timestamp'] = future_time.isoformat() + 'Z'
        
        result = validator.validate_and_enrich(invalid_telemetry)
        
        assert result.is_valid is False
        assert result.errors is not None
        assert any('too far in the future' in error for error in result.errors)
    
    def test_data_quality_warnings(self, validator, valid_telemetry):
        """Test data quality warnings generation"""
        # Test GPS at null island
        warning_telemetry = valid_telemetry.copy()
        warning_telemetry['location'] = {"lat": 0.0, "lon": 0.0}
        
        result = validator.validate_and_enrich(warning_telemetry)
        
        assert result.is_valid is True  # Valid but with warnings
        assert result.warnings is not None
        assert any('null island' in warning.lower() for warning in result.warnings)
    
    def test_identical_acceleration_warning(self, validator, valid_telemetry):
        """Test warning for identical acceleration values"""
        warning_telemetry = valid_telemetry.copy()
        warning_telemetry['acceleration'] = {"x": 5.0, "y": 5.0, "z": 5.0}
        
        result = validator.validate_and_enrich(warning_telemetry)
        
        assert result.is_valid is True
        assert result.warnings is not None
        assert any('identical' in warning.lower() for warning in result.warnings)
    
    def test_map_matching_enrichment(self, validator, valid_telemetry):
        """Test map matching and road segment enrichment"""
        # Use coordinates that should match a road segment
        telemetry = valid_telemetry.copy()
        telemetry['location'] = {"lat": 20.2961, "lon": 85.8245}  # Near urban segment
        
        result = validator.validate_and_enrich(telemetry)
        
        assert result.is_valid is True
        assert 'road_segment' in result.enriched_data
        
        road_segment = result.enriched_data['road_segment']
        assert 'segment_id' in road_segment
        assert 'speed_limit' in road_segment
        assert 'road_type' in road_segment
    
    def test_speed_violation_detection(self, validator, valid_telemetry):
        """Test speed violation detection"""
        # Set speed higher than typical speed limit
        speeding_telemetry = valid_telemetry.copy()
        speeding_telemetry['speedKmph'] = 120.0  # High speed
        speeding_telemetry['location'] = {"lat": 20.2961, "lon": 85.8245}  # Urban area (50 km/h limit)
        
        result = validator.validate_and_enrich(speeding_telemetry)
        
        assert result.is_valid is True
        assert 'speed_violation' in result.enriched_data
        
        violation = result.enriched_data['speed_violation']
        assert 'exceeded_by' in violation
        assert 'severity' in violation
        assert violation['exceeded_by'] > 0
    
    def test_derived_metrics_calculation(self, validator, valid_telemetry):
        """Test calculation of derived metrics"""
        result = validator.validate_and_enrich(valid_telemetry)
        
        assert result.is_valid is True
        enriched = result.enriched_data
        
        # Check derived metrics
        assert 'acceleration_magnitude' in enriched
        assert 'lateral_acceleration' in enriched
        assert 'driving_behavior' in enriched
        
        # Verify calculations
        accel = valid_telemetry['acceleration']
        expected_magnitude = (accel['x']**2 + accel['y']**2 + accel['z']**2)**0.5
        assert abs(enriched['acceleration_magnitude'] - expected_magnitude) < 0.001
    
    def test_geofencing_detection(self, validator, valid_telemetry):
        """Test geofencing zone detection"""
        # Place vehicle in city center
        telemetry = valid_telemetry.copy()
        telemetry['location'] = {"lat": 20.2961, "lon": 85.8245}
        
        result = validator.validate_and_enrich(telemetry)
        
        assert result.is_valid is True
        # Should detect city_center geofence
        if 'geofences' in result.enriched_data:
            assert 'city_center' in result.enriched_data['geofences']
    
    def test_toll_zone_detection(self, validator, valid_telemetry):
        """Test toll zone detection through road segments"""
        # Use highway coordinates (toll zone)
        telemetry = valid_telemetry.copy()
        telemetry['location'] = {"lat": 20.3000, "lon": 85.8300}
        
        result = validator.validate_and_enrich(telemetry)
        
        assert result.is_valid is True
        if 'road_segment' in result.enriched_data:
            road_segment = result.enriched_data['road_segment']
            # Highway segment should be toll zone
            assert road_segment.get('toll_zone') is True
    
    def test_driving_behavior_analysis(self, validator, valid_telemetry):
        """Test driving behavior analysis"""
        # Test aggressive driving
        aggressive_telemetry = valid_telemetry.copy()
        aggressive_telemetry['speedKmph'] = 90.0
        aggressive_telemetry['acceleration'] = {"x": 10.0, "y": 8.0, "z": 9.8}
        
        result = validator.validate_and_enrich(aggressive_telemetry)
        
        assert result.is_valid is True
        behavior = result.enriched_data.get('driving_behavior', {})
        assert behavior.get('aggressive_acceleration') is True
        assert behavior.get('high_speed') is True
    
    def test_eco_driving_detection(self, validator, valid_telemetry):
        """Test eco-driving behavior detection"""
        eco_telemetry = valid_telemetry.copy()
        eco_telemetry['speedKmph'] = 45.0  # Moderate speed
        eco_telemetry['acceleration'] = {"x": 1.0, "y": 0.5, "z": 9.8}  # Gentle acceleration
        
        result = validator.validate_and_enrich(eco_telemetry)
        
        assert result.is_valid is True
        behavior = result.enriched_data.get('driving_behavior', {})
        assert behavior.get('eco_driving') is True
    
    def test_dlq_message_creation(self):
        """Test dead letter queue message creation"""
        invalid_data = {"invalid": "data"}
        error_reason = "Schema validation failed"
        device_id = "DEVICE_12345678"
        
        dlq_message = create_dlq_message(invalid_data, error_reason, device_id)
        
        assert dlq_message['original_payload'] == invalid_data
        assert dlq_message['error_reason'] == error_reason
        assert dlq_message['device_id'] == device_id
        assert 'timestamp' in dlq_message
        assert 'dlq_version' in dlq_message
    
    def test_edge_case_coordinates(self, validator):
        """Test edge case GPS coordinates"""
        edge_cases = [
            {"lat": 90.0, "lon": 180.0},    # Max valid
            {"lat": -90.0, "lon": -180.0},  # Min valid
            {"lat": 0.0, "lon": 0.0},       # Null island (should warn)
        ]
        
        base_telemetry = {
            "deviceId": "DEVICE_12345678",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "speedKmph": 50.0,
            "acceleration": {"x": 1.0, "y": 1.0, "z": 9.8},
            "fuelLevel": 50.0
        }
        
        for location in edge_cases:
            telemetry = base_telemetry.copy()
            telemetry['location'] = location
            
            result = validator.validate_and_enrich(telemetry)
            
            # Should be valid but may have warnings
            assert result.is_valid is True
            
            # Null island should generate warning
            if location['lat'] == 0.0 and location['lon'] == 0.0:
                assert result.warnings is not None
                assert any('null island' in warning.lower() for warning in result.warnings)
    
    def test_boundary_speed_values(self, validator, valid_telemetry):
        """Test boundary speed values"""
        boundary_speeds = [0.0, 300.0]  # Min and max valid speeds
        
        for speed in boundary_speeds:
            telemetry = valid_telemetry.copy()
            telemetry['speedKmph'] = speed
            
            result = validator.validate_and_enrich(telemetry)
            assert result.is_valid is True
    
    def test_invalid_speed_values(self, validator, valid_telemetry):
        """Test invalid speed values"""
        invalid_speeds = [-1.0, 301.0]  # Below min and above max
        
        for speed in invalid_speeds:
            telemetry = valid_telemetry.copy()
            telemetry['speedKmph'] = speed
            
            result = validator.validate_and_enrich(telemetry)
            assert result.is_valid is False
    
    def test_enhanced_schema_fields(self, validator):
        """Test validation of enhanced schema fields"""
        enhanced_telemetry = {
            "deviceId": "DEVICE_12345678",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "location": {"lat": 20.2961, "lon": 85.8245, "altitude": 100.0},
            "speedKmph": 65.5,
            "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
            "fuelLevel": 75.5,
            "heading": 180.0,
            "gyroscope": {"x": 10.0, "y": -5.0, "z": 2.0},
            "vehicleType": "car",
            "engineData": {
                "rpm": 2500.0,
                "engineTemp": 85.0,
                "throttlePosition": 45.0,
                "brakePosition": 0.0
            },
            "diagnostics": {
                "errorCodes": ["P0001", "P0002"],
                "batteryVoltage": 12.6,
                "oilPressure": 35.0
            },
            "driverBehavior": {
                "seatbeltEngaged": True,
                "phoneUsage": False,
                "drowsinessLevel": 2.0
            }
        }
        
        result = validator.validate_and_enrich(enhanced_telemetry)
        
        assert result.is_valid is True
        assert result.enriched_data is not None
        
        # Verify all enhanced fields are preserved
        enriched = result.enriched_data
        assert enriched['gyroscope']['x'] == 10.0
        assert enriched['vehicleType'] == "car"
        assert enriched['engineData']['rpm'] == 2500.0
        assert len(enriched['diagnostics']['errorCodes']) == 2
        assert enriched['driverBehavior']['seatbeltEngaged'] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])