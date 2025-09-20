#!/usr/bin/env python3
"""
Demo Data Generator for Smart Transportation System
Generates realistic telemetry flows with various scenarios
"""

import json
import time
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import paho.mqtt.client as mqtt
import threading
import logging
import argparse
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VehicleProfile:
    """Vehicle profile for realistic simulation"""
    device_id: str
    vehicle_type: str
    driver_behavior: str  # 'normal', 'aggressive', 'cautious'
    route: List[Tuple[float, float]]  # List of (lat, lon) waypoints
    speed_preference: float  # Multiplier for speed limits
    fuel_efficiency: float  # L/100km
    
class TelemetryGenerator:
    """Generates realistic telemetry data for multiple vehicles"""
    
    def __init__(self, mqtt_host='localhost', mqtt_port=1883):
        self.mqtt_client = mqtt.Client()
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.vehicles = {}
        self.running = False
        
        # Bhubaneswar area coordinates
        self.city_center = (20.2961, 85.8245)
        self.city_bounds = {
            'north': 20.35,
            'south': 20.24,
            'east': 85.90,
            'west': 85.75
        }
        
        # Road network simulation
        self.toll_gantries = [
            {'id': 'GANTRY_001', 'location': (20.3000, 85.8300), 'name': 'NH-16 Toll Plaza'},
            {'id': 'GANTRY_002', 'location': (20.2900, 85.8200), 'name': 'Ring Road Toll'},
            {'id': 'GANTRY_003', 'location': (20.3100, 85.8400), 'name': 'Airport Road Toll'}
        ]
        
        # Setup MQTT client
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✓ Connected to MQTT broker")
        else:
            logger.error(f"✗ MQTT connection failed: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        logger.info("MQTT client disconnected")
    
    def create_vehicle_profiles(self, count: int) -> List[VehicleProfile]:
        """Create diverse vehicle profiles"""
        profiles = []
        
        vehicle_types = ['car', 'truck', 'motorcycle', 'bus']
        behavior_types = ['normal', 'aggressive', 'cautious']
        
        for i in range(count):
            device_id = f"VEHICLE_{i+1:03d}"
            vehicle_type = random.choice(vehicle_types)
            behavior = random.choice(behavior_types)
            
            # Generate route within city bounds
            route = self._generate_route()
            
            # Set characteristics based on vehicle type and behavior
            if vehicle_type == 'truck':
                speed_preference = random.uniform(0.8, 0.95)
                fuel_efficiency = random.uniform(25, 35)
            elif vehicle_type == 'motorcycle':
                speed_preference = random.uniform(1.0, 1.3)
                fuel_efficiency = random.uniform(3, 5)
            elif vehicle_type == 'bus':
                speed_preference = random.uniform(0.85, 1.0)
                fuel_efficiency = random.uniform(20, 30)
            else:  # car
                speed_preference = random.uniform(0.9, 1.2)
                fuel_efficiency = random.uniform(6, 12)
            
            # Adjust for driver behavior
            if behavior == 'aggressive':
                speed_preference *= random.uniform(1.1, 1.3)
            elif behavior == 'cautious':
                speed_preference *= random.uniform(0.7, 0.9)
            
            profile = VehicleProfile(
                device_id=device_id,
                vehicle_type=vehicle_type,
                driver_behavior=behavior,
                route=route,
                speed_preference=speed_preference,
                fuel_efficiency=fuel_efficiency
            )
            
            profiles.append(profile)
        
        return profiles
    
    def _generate_route(self) -> List[Tuple[float, float]]:
        """Generate a random route within city bounds"""
        route = []
        
        # Start point
        start_lat = random.uniform(self.city_bounds['south'], self.city_bounds['north'])
        start_lon = random.uniform(self.city_bounds['west'], self.city_bounds['east'])
        route.append((start_lat, start_lon))
        
        # Add 5-15 waypoints
        num_waypoints = random.randint(5, 15)
        current_lat, current_lon = start_lat, start_lon
        
        for _ in range(num_waypoints):
            # Move in a somewhat realistic pattern
            lat_delta = random.uniform(-0.01, 0.01)
            lon_delta = random.uniform(-0.01, 0.01)
            
            new_lat = max(self.city_bounds['south'], 
                         min(self.city_bounds['north'], current_lat + lat_delta))
            new_lon = max(self.city_bounds['west'], 
                         min(self.city_bounds['east'], current_lon + lon_delta))
            
            route.append((new_lat, new_lon))
            current_lat, current_lon = new_lat, new_lon
        
        return route
    
    def simulate_vehicle(self, profile: VehicleProfile, duration_minutes: int = 30):
        """Simulate a single vehicle's journey"""
        logger.info(f"Starting simulation for {profile.device_id} ({profile.vehicle_type}, {profile.driver_behavior})")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        # Vehicle state
        current_position = 0  # Index in route
        fuel_level = random.uniform(20, 100)
        heading = random.uniform(0, 360)
        last_toll_time = 0
        
        # Generate some invalid messages for testing
        invalid_message_probability = 0.02 if profile.driver_behavior == 'aggressive' else 0.005
        
        while time.time() < end_time and self.running:
            try:
                # Calculate current location (interpolate between waypoints)
                if current_position < len(profile.route) - 1:
                    progress = (time.time() - start_time) / (duration_minutes * 60)
                    route_progress = progress * (len(profile.route) - 1)
                    
                    waypoint_index = int(route_progress)
                    waypoint_progress = route_progress - waypoint_index
                    
                    if waypoint_index < len(profile.route) - 1:
                        lat1, lon1 = profile.route[waypoint_index]
                        lat2, lon2 = profile.route[waypoint_index + 1]
                        
                        current_lat = lat1 + (lat2 - lat1) * waypoint_progress
                        current_lon = lon1 + (lon2 - lon1) * waypoint_progress
                    else:
                        current_lat, current_lon = profile.route[-1]
                else:
                    current_lat, current_lon = profile.route[-1]
                
                # Calculate realistic speed based on time of day and behavior
                base_speed = self._calculate_speed(profile, current_lat, current_lon)
                
                # Generate acceleration data based on behavior
                accel_x, accel_y, accel_z = self._generate_acceleration(profile, base_speed)
                
                # Calculate jerk (rate of acceleration change)
                jerk = random.uniform(-2, 2)
                if profile.driver_behavior == 'aggressive':
                    jerk += random.uniform(-3, 3)
                
                # Update fuel level
                fuel_consumption = profile.fuel_efficiency * base_speed / 100000  # Rough calculation
                fuel_level = max(0, fuel_level - fuel_consumption)
                
                # Update heading based on route
                if current_position < len(profile.route) - 1:
                    next_lat, next_lon = profile.route[min(current_position + 1, len(profile.route) - 1)]
                    heading = self._calculate_bearing(current_lat, current_lon, next_lat, next_lon)
                
                # Decide whether to send invalid message
                if random.random() < invalid_message_probability:
                    self._send_invalid_message(profile.device_id)
                else:
                    # Generate valid telemetry
                    telemetry = {
                        'deviceId': profile.device_id,
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'location': {
                            'lat': round(current_lat, 6),
                            'lon': round(current_lon, 6)
                        },
                        'speedKmph': round(base_speed, 1),
                        'acceleration': {
                            'x': round(accel_x, 2),
                            'y': round(accel_y, 2),
                            'z': round(accel_z, 2)
                        },
                        'fuelLevel': round(fuel_level, 1),
                        'heading': round(heading, 1),
                        'engineData': {
                            'rpm': int(base_speed * 50 + random.uniform(-200, 200)),
                            'engineTemp': random.uniform(85, 105)
                        }
                    }
                    
                    # Send telemetry
                    self._publish_telemetry(profile.device_id, telemetry)
                    
                    # Check for toll gantry crossings
                    self._check_toll_gantries(profile, current_lat, current_lon, last_toll_time)
                    
                    # Generate events based on behavior
                    self._generate_events(profile, accel_x, accel_y, jerk, base_speed)
                
                # Sleep based on message frequency (1-5 Hz)
                sleep_time = random.uniform(0.2, 1.0)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error simulating {profile.device_id}: {e}")
                time.sleep(1)
        
        logger.info(f"Simulation completed for {profile.device_id}")
    
    def _calculate_speed(self, profile: VehicleProfile, lat: float, lon: float) -> float:
        """Calculate realistic speed based on location and time"""
        # Base speed limits by area type
        if self._is_highway_area(lat, lon):
            base_speed = 80
        elif self._is_urban_area(lat, lon):
            base_speed = 50
        else:
            base_speed = 30
        
        # Apply vehicle and behavior modifiers
        speed = base_speed * profile.speed_preference
        
        # Add some randomness
        speed += random.uniform(-10, 10)
        
        # Time of day effects
        hour = datetime.now().hour
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hour
            speed *= random.uniform(0.3, 0.7)  # Traffic congestion
        
        return max(0, min(speed, 120))  # Reasonable bounds
    
    def _is_highway_area(self, lat: float, lon: float) -> bool:
        """Check if location is in highway area"""
        # Simple heuristic based on distance from city center
        distance = self._calculate_distance(lat, lon, self.city_center[0], self.city_center[1])
        return distance > 5  # km
    
    def _is_urban_area(self, lat: float, lon: float) -> bool:
        """Check if location is in urban area"""
        distance = self._calculate_distance(lat, lon, self.city_center[0], self.city_center[1])
        return distance <= 2  # km
    
    def _generate_acceleration(self, profile: VehicleProfile, speed: float) -> Tuple[float, float, float]:
        """Generate realistic acceleration data"""
        # Base acceleration
        accel_x = random.uniform(-1, 1)
        accel_y = random.uniform(-1, 1)
        accel_z = random.uniform(9.5, 10.2)  # Gravity + vehicle dynamics
        
        # Behavior-based modifications
        if profile.driver_behavior == 'aggressive':
            # More extreme accelerations
            if random.random() < 0.1:  # 10% chance of harsh event
                accel_x += random.choice([-1, 1]) * random.uniform(4, 8)
                accel_y += random.choice([-1, 1]) * random.uniform(3, 6)
        elif profile.driver_behavior == 'cautious':
            # Smoother accelerations
            accel_x *= 0.5
            accel_y *= 0.5
        
        return accel_x, accel_y, accel_z
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing between two points"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        y = math.sin(delta_lon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _check_toll_gantries(self, profile: VehicleProfile, lat: float, lon: float, last_toll_time: float):
        """Check if vehicle is near toll gantries"""
        current_time = time.time()
        
        for gantry in self.toll_gantries:
            distance = self._calculate_distance(lat, lon, gantry['location'][0], gantry['location'][1])
            
            # If within 100m of gantry and haven't triggered recently
            if distance < 0.1 and (current_time - last_toll_time) > 300:  # 5 minutes cooldown
                self._trigger_toll_event(profile, gantry)
                last_toll_time = current_time
    
    def _trigger_toll_event(self, profile: VehicleProfile, gantry: Dict[str, Any]):
        """Trigger toll charging event"""
        logger.info(f"🚧 {profile.device_id} crossing {gantry['name']}")
        
        # Send toll event via API (simulate)
        toll_data = {
            'device_id': profile.device_id,
            'gantry_id': gantry['id'],
            'vehicle_type': profile.vehicle_type,
            'location': {
                'lat': gantry['location'][0],
                'lon': gantry['location'][1]
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }\n        \n        # In a real scenario, this would call the API\n        # For demo, just log the event\n        logger.info(f\"Toll event: {json.dumps(toll_data)}\")\n    \n    def _generate_events(self, profile: VehicleProfile, accel_x: float, accel_y: float, jerk: float, speed: float):\n        \"\"\"Generate driving events based on telemetry\"\"\"\n        # Harsh braking detection\n        if accel_x < -6 or abs(jerk) > 4:\n            event = {\n                'deviceId': profile.device_id,\n                'eventType': 'HARSH_BRAKE',\n                'timestamp': datetime.utcnow().isoformat() + 'Z',\n                'location': {'lat': 20.2961, 'lon': 85.8245},  # Simplified\n                'speedBefore': speed + 20,\n                'speedAfter': speed,\n                'accelPeak': accel_x,\n                'severity': 'HIGH' if accel_x < -8 else 'MEDIUM'\n            }\n            self._publish_event(profile.device_id, event)\n        \n        # Harsh acceleration detection\n        elif accel_x > 6:\n            event = {\n                'deviceId': profile.device_id,\n                'eventType': 'HARSH_ACCEL',\n                'timestamp': datetime.utcnow().isoformat() + 'Z',\n                'location': {'lat': 20.2961, 'lon': 85.8245},\n                'speedBefore': speed - 15,\n                'speedAfter': speed,\n                'accelPeak': accel_x,\n                'severity': 'HIGH' if accel_x > 8 else 'MEDIUM'\n            }\n            self._publish_event(profile.device_id, event)\n        \n        # Speed violation (random chance)\n        elif speed > 80 and random.random() < 0.05:  # 5% chance when speeding\n            event = {\n                'deviceId': profile.device_id,\n                'eventType': 'SPEED_VIOLATION',\n                'timestamp': datetime.utcnow().isoformat() + 'Z',\n                'location': {'lat': 20.2961, 'lon': 85.8245},\n                'currentSpeed': speed,\n                'speedLimit': 50,\n                'violation': speed - 50\n            }\n            self._publish_event(profile.device_id, event)\n    \n    def _send_invalid_message(self, device_id: str):\n        \"\"\"Send invalid message for testing validation\"\"\"\n        invalid_types = [\n            # Missing required fields\n            {'deviceId': device_id, 'timestamp': datetime.utcnow().isoformat() + 'Z'},\n            # Invalid data types\n            {'deviceId': device_id, 'timestamp': 'invalid-timestamp', 'location': {'lat': 'invalid', 'lon': 85.8245}},\n            # Out of range values\n            {'deviceId': device_id, 'timestamp': datetime.utcnow().isoformat() + 'Z', 'speedKmph': 500},\n            # Malformed JSON (will be sent as string)\n            '{\"deviceId\": \"' + device_id + '\", \"invalid\": json}'\n        ]\n        \n        invalid_msg = random.choice(invalid_types)\n        \n        if isinstance(invalid_msg, str):\n            # Send malformed JSON\n            self.mqtt_client.publish(f\"/org/demo/device/{device_id}/telemetry\", invalid_msg)\n        else:\n            # Send invalid but valid JSON\n            self.mqtt_client.publish(f\"/org/demo/device/{device_id}/telemetry\", json.dumps(invalid_msg))\n        \n        logger.warning(f\"📤 Sent invalid message from {device_id}\")\n    \n    def _publish_telemetry(self, device_id: str, telemetry: Dict[str, Any]):\n        \"\"\"Publish telemetry to MQTT\"\"\"\n        topic = f\"/org/demo/device/{device_id}/telemetry\"\n        self.mqtt_client.publish(topic, json.dumps(telemetry))\n    \n    def _publish_event(self, device_id: str, event: Dict[str, Any]):\n        \"\"\"Publish event to MQTT\"\"\"\n        topic = f\"/org/demo/device/{device_id}/events\"\n        self.mqtt_client.publish(topic, json.dumps(event))\n        logger.info(f\"🚨 Event: {event['eventType']} from {device_id}\")\n    \n    def start_simulation(self, num_vehicles: int = 10, duration_minutes: int = 30):\n        \"\"\"Start the full simulation\"\"\"\n        logger.info(f\"🚀 Starting simulation with {num_vehicles} vehicles for {duration_minutes} minutes\")\n        \n        # Connect to MQTT\n        try:\n            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)\n            self.mqtt_client.loop_start()\n        except Exception as e:\n            logger.error(f\"Failed to connect to MQTT: {e}\")\n            return\n        \n        # Create vehicle profiles\n        profiles = self.create_vehicle_profiles(num_vehicles)\n        \n        # Start simulation threads\n        self.running = True\n        threads = []\n        \n        for profile in profiles:\n            thread = threading.Thread(\n                target=self.simulate_vehicle,\n                args=(profile, duration_minutes),\n                daemon=True\n            )\n            thread.start()\n            threads.append(thread)\n            \n            # Stagger vehicle starts\n            time.sleep(random.uniform(1, 5))\n        \n        try:\n            # Wait for all threads to complete\n            for thread in threads:\n                thread.join()\n        except KeyboardInterrupt:\n            logger.info(\"Simulation interrupted by user\")\n            self.running = False\n        \n        # Cleanup\n        self.mqtt_client.loop_stop()\n        self.mqtt_client.disconnect()\n        \n        logger.info(\"✅ Simulation completed\")\n\ndef main():\n    parser = argparse.ArgumentParser(description='Generate demo telemetry data')\n    parser.add_argument('--vehicles', type=int, default=10, help='Number of vehicles to simulate')\n    parser.add_argument('--duration', type=int, default=30, help='Simulation duration in minutes')\n    parser.add_argument('--mqtt-host', type=str, default='localhost', help='MQTT broker host')\n    parser.add_argument('--mqtt-port', type=int, default=1883, help='MQTT broker port')\n    \n    args = parser.parse_args()\n    \n    generator = TelemetryGenerator(args.mqtt_host, args.mqtt_port)\n    generator.start_simulation(args.vehicles, args.duration)\n\nif __name__ == \"__main__\":\n    main()