#!/usr/bin/env python3
"""
Enhanced unit tests for telemetry validation and dead letter queue
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os

# Add stream_processor to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'stream_processor'))

from validator import TelemetryValidator, DeadLetterQueue

class TestTelemetryValidator:
    
    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return TelemetryValidator()
    
    @pytest.fixture
    def valid_telemetry(self):
        """Valid telemetry message"""
        return {
            "deviceId": "DEVICE_TEST_001",
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {
                "lat": 20.2961,
                "lon": 85.8245
            },
            "speedKmph": 45.5,
            "acceleration": {
                "x": 1.2,
                "y": -0.8,
                "z": 9.8
            },
            "fuelLevel": 75.5,
            "heading": 180.0
        }
    
    def test_valid_message_validation(self, validator, valid_telemetry):
        """Test validation of valid message"""
        is_valid, error_msg = validator.validate_message(valid_telemetry)
        assert is_valid is True
        assert error_msg is None
    
    def test_missing_required_field(self, validator, valid_telemetry):
        """Test validation fails for missing required field"""
        del valid_telemetry['deviceId']
        is_valid, error_msg = validator.validate_message(valid_telemetry)
        assert is_valid is False
        assert 'deviceId' in error_msg
    
    def test_invalid_location_format(self, validator, valid_telemetry):
        """Test validation fails for invalid location"""
        valid_telemetry['location'] = {"lat": 20.2961}  # Missing lon
        is_valid, error_msg = validator.validate_message(valid_telemetry)
        assert is_valid is False
        assert 'lon' in error_msg
    
    def test_invalid_acceleration_format(self, validator, valid_telemetry):
        """Test validation fails for invalid acceleration"""
        valid_telemetry['acceleration'] = {"x": 1.2, "y": -0.8}  # Missing z
        is_valid, error_msg = validator.validate_message(valid_telemetry)
        assert is_valid is False
        assert 'z' in error_msg
    
    def test_speed_out_of_range(self, validator, valid_telemetry):
        """Test validation fails for speed out of range"""
        valid_telemetry['speedKmph'] = 350  # Above maximum
        is_valid, error_msg = validator.validate_message(valid_telemetry)
        assert is_valid is False
        assert 'speedKmph' in error_msg
    
    def test_optional_fields_missing(self, validator, valid_telemetry):
        """Test validation passes with optional fields missing"""
        del valid_telemetry['fuelLevel']
        del valid_telemetry['heading']
        is_valid, error_msg = validator.validate_message(valid_telemetry)
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_and_enrich_valid(self, validator, valid_telemetry):
        """Test validate_and_enrich with valid message"""
        is_valid, enriched, error_msg = validator.validate_and_enrich(valid_telemetry, "DEVICE_TEST_001")
        
        assert is_valid is True
        assert error_msg is None
        assert '_metadata' in enriched
        assert enriched['_metadata']['validator'] == 'TelemetryValidator'
    
    def test_validate_and_enrich_missing_device_id(self, validator, valid_telemetry):
        """Test validate_and_enrich adds missing deviceId"""
        del valid_telemetry['deviceId']
        is_valid, enriched, error_msg = validator.validate_and_enrich(valid_telemetry, "DEVICE_TEST_001")
        
        assert is_valid is True
        assert enriched['deviceId'] == "DEVICE_TEST_001"
    
    def test_validate_and_enrich_device_id_mismatch(self, validator, valid_telemetry):
        """Test validate_and_enrich fails on device ID mismatch"""
        valid_telemetry['deviceId'] = "DIFFERENT_DEVICE"
        is_valid, enriched, error_msg = validator.validate_and_enrich(valid_telemetry, "DEVICE_TEST_001")
        
        assert is_valid is False
        assert "Device ID mismatch" in error_msg
    
    def test_validate_and_enrich_adds_timestamp(self, validator, valid_telemetry):
        """Test validate_and_enrich adds timestamp if missing"""
        del valid_telemetry['timestamp']
        is_valid, enriched, error_msg = validator.validate_and_enrich(valid_telemetry, "DEVICE_TEST_001")
        
        assert is_valid is True
        assert 'timestamp' in enriched
        assert enriched['timestamp'].endswith('Z')

class TestDeadLetterQueue:
    
    @pytest.fixture
    def mock_kafka_producer(self):
        """Mock Kafka producer"""
        return Mock()
    
    @pytest.fixture
    def dlq(self, mock_kafka_producer):
        """Create DLQ instance"""
        return DeadLetterQueue(mock_kafka_producer)
    
    def test_send_to_dlq_success(self, dlq, mock_kafka_producer):
        """Test successful DLQ message sending"""
        original_message = {"invalid": "data"}
        error_reason = "Missing required field"
        device_id = "DEVICE_001"
        
        dlq.send_to_dlq(original_message, error_reason, device_id)
        
        # Verify Kafka producer was called
        mock_kafka_producer.send.assert_called_once()
        call_args = mock_kafka_producer.send.call_args
        
        assert call_args[1]['key'] == device_id
        assert call_args[0][0] == 'transport.dlq'
        
        dlq_message = call_args[1]['value']
        assert dlq_message['original_message'] == original_message
        assert dlq_message['error_reason'] == error_reason
        assert dlq_message['device_id'] == device_id
    
    def test_send_to_dlq_with_metadata(self, dlq, mock_kafka_producer):
        """Test DLQ message with metadata"""
        metadata = {"source": "mqtt", "topic": "/test/topic"}
        
        dlq.send_to_dlq("invalid", "error", "device", metadata=metadata)
        
        call_args = mock_kafka_producer.send.call_args
        dlq_message = call_args[1]['value']
        assert dlq_message['metadata'] == metadata
    
    def test_dlq_stats_tracking(self, dlq, mock_kafka_producer):
        """Test DLQ statistics tracking"""
        initial_stats = dlq.get_stats()
        assert initial_stats['total_messages'] == 0
        
        dlq.send_to_dlq("msg1", "error1", "dev1", "validation_error")
        dlq.send_to_dlq("msg2", "error2", "dev2", "json_error")
        
        stats = dlq.get_stats()
        assert stats['total_messages'] == 2
        assert stats['validation_errors'] == 1
        assert stats['json_errors'] == 1
    
    def test_send_to_dlq_kafka_failure(self, dlq, mock_kafka_producer):
        """Test DLQ handling when Kafka send fails"""
        mock_kafka_producer.send.side_effect = Exception("Kafka error")
        
        # Should not raise exception
        dlq.send_to_dlq("message", "error", "device")
        
        # Stats should not be updated on failure
        stats = dlq.get_stats()
        assert stats['total_messages'] == 0

if __name__ == "__main__":
    pytest.main([__file__])