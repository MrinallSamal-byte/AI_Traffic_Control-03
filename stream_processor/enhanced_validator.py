#!/usr/bin/env python3
"""
Enhanced Telemetry Validator with Dead Letter Queue and Map Matching
"""

import json
import jsonschema
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import math
import os

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of telemetry validation"""
    is_valid: bool
    enriched_data: Optional[Dict[str, Any]] = None
    errors: Optional[list] = None
    warnings: Optional[list] = None

@dataclass
class RoadSegment:
    """Road segment information for map matching"""
    segment_id: str
    speed_limit: int
    road_type: str
    toll_zone: bool = False
    coordinates: Tuple[float, float] = None

class EnhancedTelemetryValidator:
    """Enhanced validator with schema validation, enrichment, and map matching"""
    
    def __init__(self, schema_path: str = None):
        self.schema = self._load_schema(schema_path)
        self.road_segments = self._load_road_segments()
        
    def _load_schema(self, schema_path: str = None) -> dict:
        """Load JSON schema for validation"""
        if not schema_path:
            schema_path = os.path.join(os.path.dirname(__file__), 'schema', 'telemetry.json')
        
        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            return {}
    
    def _load_road_segments(self) -> Dict[str, RoadSegment]:
        """Load road segment data for map matching"""
        # Mock road segments - in production, load from database/GIS service
        return {
            "SEG_20296_85824": RoadSegment(
                segment_id="SEG_20296_85824",
                speed_limit=50,
                road_type="urban",
                toll_zone=False,
                coordinates=(20.2961, 85.8245)
            ),
            "SEG_20300_85830": RoadSegment(
                segment_id="SEG_20300_85830", 
                speed_limit=100,
                road_type="highway",
                toll_zone=True,
                coordinates=(20.3000, 85.8300)
            ),
            "SEG_20290_85820": RoadSegment(
                segment_id="SEG_20290_85820",
                speed_limit=30,
                road_type="residential", 
                toll_zone=False,
                coordinates=(20.2900, 85.8200)
            )
        }
    
    def validate_and_enrich(self, telemetry_data: Dict[str, Any]) -> ValidationResult:
        """Validate telemetry data and enrich with additional information"""
        errors = []
        warnings = []
        
        try:
            # 1. JSON Schema validation
            jsonschema.validate(telemetry_data, self.schema)
            
            # 2. Business logic validation
            business_errors = self._validate_business_rules(telemetry_data)
            if business_errors:
                errors.extend(business_errors)
            
            # 3. Data quality checks
            quality_warnings = self._check_data_quality(telemetry_data)
            if quality_warnings:
                warnings.extend(quality_warnings)
            
            # If validation failed, return early
            if errors:
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings
                )
            
            # 4. Enrich with additional data
            enriched_data = self._enrich_telemetry(telemetry_data.copy())
            
            return ValidationResult(
                is_valid=True,
                enriched_data=enriched_data,
                warnings=warnings
            )
            
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
            return ValidationResult(is_valid=False, errors=errors)
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors)
    
    def _validate_business_rules(self, data: Dict[str, Any]) -> list:
        """Apply business logic validation rules"""
        errors = []
        
        # Check for realistic speed vs acceleration correlation
        speed = data.get('speedKmph', 0)
        accel = data.get('acceleration', {})
        accel_magnitude = math.sqrt(
            accel.get('x', 0)**2 + accel.get('y', 0)**2 + accel.get('z', 0)**2
        )
        
        # Unrealistic acceleration for given speed
        if speed > 0 and accel_magnitude > 20:
            errors.append("Unrealistic acceleration magnitude for current speed")
        
        # Check fuel level consistency
        fuel_level = data.get('fuelLevel')
        if fuel_level is not None and fuel_level < 0:
            errors.append("Fuel level cannot be negative")
        
        # Check timestamp is not too far in future
        timestamp_str = data.get('timestamp')
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                now = datetime.now(timestamp.tzinfo)
                if (timestamp - now).total_seconds() > 300:  # 5 minutes in future
                    errors.append("Timestamp is too far in the future")
            except ValueError:
                errors.append("Invalid timestamp format")
        
        return errors
    
    def _check_data_quality(self, data: Dict[str, Any]) -> list:
        """Check data quality and generate warnings"""
        warnings = []
        
        # Check for suspicious patterns
        location = data.get('location', {})
        lat, lon = location.get('lat'), location.get('lon')
        
        # Check if coordinates are at exactly 0,0 (likely GPS error)
        if lat == 0.0 and lon == 0.0:
            warnings.append("GPS coordinates at null island (0,0) - possible GPS error")
        
        # Check for repeated identical values (sensor stuck)
        accel = data.get('acceleration', {})
        if (accel.get('x') == accel.get('y') == accel.get('z') and 
            accel.get('x') is not None):
            warnings.append("All acceleration values identical - possible sensor malfunction")
        
        # Check for missing optional but important fields
        if not data.get('heading'):
            warnings.append("Missing heading information")
        
        if not data.get('fuelLevel'):
            warnings.append("Missing fuel level information")
        
        return warnings
    
    def _enrich_telemetry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich telemetry data with additional information"""
        
        # Add processing metadata
        data['processed_at'] = datetime.utcnow().isoformat() + 'Z'
        data['validator_version'] = '1.0.0'
        
        # Map matching - find nearest road segment
        location = data.get('location', {})
        lat, lon = location.get('lat'), location.get('lon')
        
        if lat is not None and lon is not None:
            road_segment = self._find_nearest_road_segment(lat, lon)
            if road_segment:
                data['road_segment'] = {
                    'segment_id': road_segment.segment_id,
                    'speed_limit': road_segment.speed_limit,
                    'road_type': road_segment.road_type,
                    'toll_zone': road_segment.toll_zone
                }
                
                # Check for speed violations
                current_speed = data.get('speedKmph', 0)
                if current_speed > road_segment.speed_limit * 1.1:  # 10% tolerance
                    data['speed_violation'] = {
                        'exceeded_by': current_speed - road_segment.speed_limit,
                        'severity': 'high' if current_speed > road_segment.speed_limit * 1.5 else 'medium'
                    }
        
        # Calculate derived metrics
        self._add_derived_metrics(data)
        
        # Add geofencing information
        self._add_geofencing_info(data)
        
        return data
    
    def _find_nearest_road_segment(self, lat: float, lon: float) -> Optional[RoadSegment]:
        """Find nearest road segment using simple distance calculation"""
        min_distance = float('inf')
        nearest_segment = None
        
        for segment in self.road_segments.values():
            if segment.coordinates:
                seg_lat, seg_lon = segment.coordinates
                distance = math.sqrt((lat - seg_lat)**2 + (lon - seg_lon)**2)
                if distance < min_distance:
                    min_distance = distance
                    nearest_segment = segment
        
        # Return segment if within reasonable distance (0.01 degrees ≈ 1km)
        return nearest_segment if min_distance < 0.01 else None
    
    def _add_derived_metrics(self, data: Dict[str, Any]):
        """Add calculated metrics from raw telemetry"""
        
        # Calculate acceleration magnitude
        accel = data.get('acceleration', {})
        if all(k in accel for k in ['x', 'y', 'z']):
            accel_magnitude = math.sqrt(accel['x']**2 + accel['y']**2 + accel['z']**2)
            data['acceleration_magnitude'] = round(accel_magnitude, 3)
            
            # Calculate lateral acceleration (for cornering analysis)
            lateral_accel = math.sqrt(accel['x']**2 + accel['y']**2)
            data['lateral_acceleration'] = round(lateral_accel, 3)
        
        # Calculate jerk (rate of acceleration change) if previous data available
        # This would require storing previous telemetry - simplified for demo
        data['jerk_estimate'] = 0.0
        
        # Add driving behavior indicators
        speed = data.get('speedKmph', 0)
        if speed > 0:
            data['driving_behavior'] = {
                'aggressive_acceleration': accel_magnitude > 8 if 'accel_magnitude' in locals() else False,
                'high_speed': speed > 80,
                'eco_driving': speed < 60 and accel_magnitude < 2 if 'accel_magnitude' in locals() else False
            }
    
    def _add_geofencing_info(self, data: Dict[str, Any]):
        """Add geofencing and zone information"""
        location = data.get('location', {})
        lat, lon = location.get('lat'), location.get('lon')
        
        if lat is not None and lon is not None:
            # Define geofences (in production, load from database)
            geofences = {
                'city_center': {'lat': 20.2961, 'lon': 85.8245, 'radius': 0.005},
                'industrial_zone': {'lat': 20.3000, 'lon': 85.8300, 'radius': 0.008},
                'residential_area': {'lat': 20.2900, 'lon': 85.8200, 'radius': 0.003}
            }
            
            active_zones = []
            for zone_name, zone_data in geofences.items():
                distance = math.sqrt(
                    (lat - zone_data['lat'])**2 + (lon - zone_data['lon'])**2
                )
                if distance <= zone_data['radius']:
                    active_zones.append(zone_name)
            
            if active_zones:
                data['geofences'] = active_zones

def create_dlq_message(original_data: Any, error_reason: str, device_id: str = None) -> Dict[str, Any]:
    """Create dead letter queue message for invalid telemetry"""
    return {
        'original_payload': original_data,
        'error_reason': error_reason,
        'device_id': device_id or 'unknown',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'dlq_version': '1.0.0'
    }

if __name__ == "__main__":
    # Test the validator
    validator = EnhancedTelemetryValidator()
    
    # Test valid message
    valid_telemetry = {
        "deviceId": "DEVICE_12345678",
        "timestamp": "2024-01-15T10:30:00Z",
        "location": {"lat": 20.2961, "lon": 85.8245},
        "speedKmph": 65.5,
        "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
        "fuelLevel": 75.5
    }
    
    result = validator.validate_and_enrich(valid_telemetry)
    print(f"Validation result: {result.is_valid}")
    if result.enriched_data:
        print(f"Road segment: {result.enriched_data.get('road_segment')}")