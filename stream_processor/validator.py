#!/usr/bin/env python3
"""
Telemetry Validator with JSON Schema and Dead Letter Queue
"""

import json
import jsonschema
from jsonschema import validate, ValidationError
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class TelemetryValidator:
    def __init__(self, schema_path: str = None):
        """Initialize validator with JSON schema"""
        if schema_path is None:
            schema_path = os.path.join(os.path.dirname(__file__), 'schema', 'telemetry.json')
        
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
        
        logger.info(f"Loaded telemetry schema from {schema_path}")
    
    def validate_message(self, message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate telemetry message against JSON schema
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            validate(instance=message, schema=self.schema)
            return True, None
        except ValidationError as e:
            error_msg = f"Schema validation failed: {e.message} at path: {'.'.join(str(p) for p in e.absolute_path)}"
            return False, error_msg
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            return False, error_msg
    
    def validate_and_enrich(self, message: Dict[str, Any], device_id: str) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Validate message and add enrichment data
        
        Returns:
            Tuple[bool, Dict[str, Any], Optional[str]]: (is_valid, enriched_message, error_message)
        """
        # Basic enrichment
        enriched = message.copy()
        
        # Ensure deviceId matches
        if 'deviceId' not in enriched:
            enriched['deviceId'] = device_id
        elif enriched['deviceId'] != device_id:
            return False, enriched, f"Device ID mismatch: message={enriched['deviceId']}, topic={device_id}"
        
        # Add timestamp if missing
        if 'timestamp' not in enriched:
            enriched['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Validate enriched message
        is_valid, error_msg = self.validate_message(enriched)
        
        if is_valid:
            # Add processing metadata
            enriched['_metadata'] = {
                'validated_at': datetime.utcnow().isoformat() + 'Z',
                'schema_version': '1.0',
                'validator': 'TelemetryValidator'
            }
        
        return is_valid, enriched, error_msg

class DeadLetterQueue:
    def __init__(self, kafka_producer, dlq_topic: str = 'transport.dlq'):
        """Initialize dead letter queue handler"""
        self.kafka_producer = kafka_producer
        self.dlq_topic = dlq_topic
        self.stats = {
            'total_messages': 0,
            'validation_errors': 0,
            'processing_errors': 0,
            'json_errors': 0
        }
    
    def send_to_dlq(self, original_message: Any, error_reason: str, device_id: str, 
                   error_type: str = 'validation_error', metadata: Dict[str, Any] = None):
        """Send invalid message to dead letter queue"""
        dlq_message = {
            'original_message': original_message,
            'error_reason': error_reason,
            'error_type': error_type,
            'device_id': device_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'metadata': metadata or {}
        }
        
        try:
            self.kafka_producer.send(
                self.dlq_topic,
                key=device_id,
                value=dlq_message
            )
            
            # Update stats
            self.stats['total_messages'] += 1
            self.stats[f'{error_type}s'] = self.stats.get(f'{error_type}s', 0) + 1
            
            logger.warning(f"Sent message to DLQ: {error_reason} (device: {device_id})")
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get DLQ statistics"""
        return self.stats.copy()