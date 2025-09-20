#!/usr/bin/env python3
"""
Sample telemetry data generator for testing the Smart Transportation System
"""

import json
import random
import time
from datetime import datetime, timedelta
import argparse
import requests
import paho.mqtt.client as mqtt
from typing import List, Dict, Any

class TelemetryGenerator:
    def __init__(self, mqtt_host='localhost', mqtt_port=1883, api_base_url='http://localhost:5000'):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.api_base_url = api_base_url
        self.mqtt_client = None
        self.access_token = None
        
        # Base coordinates (Bhubaneswar, India)
        self.base_lat = 20.2961
        self.base_lon = 85.8245
        
        # Vehicle types and their characteristics
        self.vehicle_types = {
            'car': {'max_speed': 120, 'fuel_capacity': 50, 'accel_range': (-3, 3)},
            'truck': {'max_speed': 80, 'fuel_capacity': 200, 'accel_range': (-2, 2)},
            'motorcycle': {'max_speed': 100, 'fuel_capacity': 15, 'accel_range': (-4, 4)}
        }
    
    def setup_mqtt(self):
        """Setup MQTT client connection"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            print(f"✓ Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to MQTT broker: {e}")
            return False
    
    def authenticate_api(self, username='admin', password='password'):
        """Authenticate with API server"""
        try:
            response = requests.post(
                f"{self.api_base_url}/auth/login",
                json={'username': username, 'password': password},
                timeout=10
            )
            
            if response.status_code == 200:
                self.access_token = response.json()['access_token']
                print(f"✓ Authenticated with API server")
                return True
            else:
                print(f"✗ Authentication failed: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Failed to authenticate: {e}")
            return False
    
    def generate_device_id(self, index: int) -> str:
        """Generate a valid device ID"""
        return f"DEVICE_{index:08d}"
    
    def generate_location(self, device_index: int, time_offset: int) -> Dict[str, float]:
        """Generate realistic location data with movement patterns"""
        # Create different movement patterns for different devices
        pattern = device_index % 4
        
        if pattern == 0:  # Circular movement
            angle = (time_offset * 0.01) % (2 * 3.14159)
            radius = 0.01
            lat = self.base_lat + radius * random.uniform(0.8, 1.2) * (1 + 0.3 * (time_offset % 100) / 100)
            lon = self.base_lon + radius * random.uniform(0.8, 1.2) * (1 + 0.3 * (time_offset % 100) / 100)
        elif pattern == 1:  # Linear movement
            lat = self.base_lat + (time_offset * 0.0001) % 0.02 - 0.01
            lon = self.base_lon + (time_offset * 0.0001) % 0.02 - 0.01
        elif pattern == 2:  # Random walk
            lat = self.base_lat + random.uniform(-0.015, 0.015)
            lon = self.base_lon + random.uniform(-0.015, 0.015)
        else:  # Highway pattern
            lat = self.base_lat + 0.005 + (time_offset * 0.0002) % 0.01
            lon = self.base_lon + random.uniform(-0.002, 0.002)
        
        return {
            'lat': round(lat, 6),
            'lon': round(lon, 6),
            'altitude': round(random.uniform(50, 200), 1)
        }
    
    def generate_speed(self, vehicle_type: str, time_offset: int) -> float:
        """Generate realistic speed data"""
        max_speed = self.vehicle_types[vehicle_type]['max_speed']
        
        # Create speed patterns based on time
        if time_offset % 120 < 30:  # Acceleration phase
            base_speed = min(max_speed * 0.8, (time_offset % 30) * 2)
        elif time_offset % 120 < 90:  # Cruising phase
            base_speed = max_speed * random.uniform(0.6, 0.9)
        else:  # Deceleration phase
            base_speed = max_speed * random.uniform(0.2, 0.5)
        
        # Add some randomness
        speed = base_speed + random.uniform(-5, 5)
        return max(0, min(max_speed, round(speed, 1)))
    
    def generate_acceleration(self, vehicle_type: str, prev_speed: float, current_speed: float) -> Dict[str, float]:
        """Generate realistic acceleration data"""
        accel_range = self.vehicle_types[vehicle_type]['accel_range']
        
        # Calculate longitudinal acceleration based on speed change
        speed_diff = current_speed - prev_speed
        accel_x = speed_diff * 0.1 + random.uniform(-0.5, 0.5)
        
        # Lateral acceleration (turning)
        accel_y = random.uniform(-2, 2) if random.random() < 0.3 else random.uniform(-0.5, 0.5)
        
        # Vertical acceleration (road bumps, etc.)
        accel_z = 9.8 + random.uniform(-0.5, 0.5)
        
        return {
            'x': round(max(accel_range[0], min(accel_range[1], accel_x)), 2),
            'y': round(max(accel_range[0], min(accel_range[1], accel_y)), 2),
            'z': round(accel_z, 2)
        }
    
    def generate_fuel_level(self, device_index: int, time_offset: int) -> float:
        """Generate realistic fuel level data"""
        # Fuel decreases over time with some randomness
        base_fuel = 100 - (time_offset * 0.05) % 80
        fuel_level = base_fuel + random.uniform(-5, 5)
        return max(5, min(100, round(fuel_level, 1)))
    
    def generate_telemetry_message(self, device_index: int, time_offset: int, prev_speed: float = 0) -> Dict[str, Any]:
        """Generate a complete telemetry message"""
        device_id = self.generate_device_id(device_index)
        vehicle_type = list(self.vehicle_types.keys())[device_index % len(self.vehicle_types)]
        
        timestamp = (datetime.utcnow() + timedelta(seconds=time_offset)).isoformat() + 'Z'
        location = self.generate_location(device_index, time_offset)
        speed = self.generate_speed(vehicle_type, time_offset)
        acceleration = self.generate_acceleration(vehicle_type, prev_speed, speed)
        fuel_level = self.generate_fuel_level(device_index, time_offset)
        
        message = {
            'deviceId': device_id,
            'timestamp': timestamp,
            'location': location,
            'speedKmph': speed,
            'acceleration': acceleration,
            'fuelLevel': fuel_level,
            'heading': round(random.uniform(0, 360), 1),
            'engineData': {
                'rpm': round(speed * 30 + random.uniform(-200, 200), 0),
                'engineTemp': round(random.uniform(80, 95), 1)
            },
            'diagnostics': {
                'errorCodes': [] if random.random() > 0.05 else [f"P{random.randint(1000, 9999)}"],
                'batteryVoltage': round(random.uniform(12.0, 14.5), 1)
            }
        }
        
        return message, speed
    
    def send_via_mqtt(self, device_id: str, message: Dict[str, Any]):
        """Send telemetry message via MQTT"""
        if not self.mqtt_client:
            return False
        
        topic = f"/org/transport/device/{device_id}/telemetry"
        payload = json.dumps(message)
        
        try:
            result = self.mqtt_client.publish(topic, payload)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"✗ MQTT publish error: {e}")
            return False
    
    def send_via_api(self, message: Dict[str, Any]):
        """Send telemetry message via API"""
        if not self.access_token:
            return False
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f"{self.api_base_url}/telemetry/ingest",
                json=message,
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"✗ API send error: {e}")
            return False
    
    def generate_harsh_driving_event(self, device_index: int) -> Dict[str, Any]:
        """Generate a harsh driving event"""
        device_id = self.generate_device_id(device_index)
        
        event_types = ['HARSH_BRAKE', 'HARSH_ACCEL', 'SHARP_TURN', 'SPEED_VIOLATION']
        event_type = random.choice(event_types)
        
        event = {
            'deviceId': device_id,
            'eventType': event_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'location': self.generate_location(device_index, 0),
            'speedBefore': random.uniform(60, 100),
            'speedAfter': random.uniform(20, 40),
            'accelPeak': random.uniform(6, 12),
            'metadata': {
                'severity': random.choice(['LOW', 'MEDIUM', 'HIGH']),
                'duration': random.uniform(1, 5)
            }
        }
        
        return event
    
    def send_event_via_mqtt(self, device_id: str, event: Dict[str, Any]):
        """Send event via MQTT"""
        if not self.mqtt_client:
            return False
        
        topic = f"/org/transport/device/{device_id}/events"
        payload = json.dumps(event)
        
        try:
            result = self.mqtt_client.publish(topic, payload)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"✗ MQTT event publish error: {e}")
            return False
    
    def run_simulation(self, num_devices: int = 10, duration_seconds: int = 300, 
                      interval_seconds: float = 2.0, use_mqtt: bool = True, use_api: bool = False):
        """Run telemetry simulation"""
        print(f"🚀 Starting telemetry simulation:")
        print(f"   Devices: {num_devices}")
        print(f"   Duration: {duration_seconds} seconds")
        print(f"   Interval: {interval_seconds} seconds")
        print(f"   MQTT: {'✓' if use_mqtt else '✗'}")
        print(f"   API: {'✓' if use_api else '✗'}")
        
        # Setup connections
        if use_mqtt and not self.setup_mqtt():
            print("Failed to setup MQTT, disabling MQTT mode")
            use_mqtt = False
        
        if use_api and not self.authenticate_api():
            print("Failed to authenticate API, disabling API mode")
            use_api = False
        
        if not use_mqtt and not use_api:
            print("✗ No valid transport method available")
            return
        
        # Track previous speeds for acceleration calculation
        prev_speeds = [0.0] * num_devices
        
        start_time = time.time()
        message_count = 0
        event_count = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                iteration_start = time.time()
                
                for device_index in range(num_devices):
                    # Generate telemetry message
                    message, current_speed = self.generate_telemetry_message(
                        device_index, 
                        int(time.time() - start_time),
                        prev_speeds[device_index]
                    )
                    prev_speeds[device_index] = current_speed
                    
                    # Send telemetry
                    sent = False
                    if use_mqtt:
                        sent = self.send_via_mqtt(message['deviceId'], message)
                    elif use_api:
                        sent = self.send_via_api(message)
                    
                    if sent:
                        message_count += 1
                    
                    # Occasionally generate events
                    if random.random() < 0.05:  # 5% chance
                        event = self.generate_harsh_driving_event(device_index)
                        if use_mqtt:
                            if self.send_event_via_mqtt(event['deviceId'], event):
                                event_count += 1
                
                # Progress update
                elapsed = time.time() - start_time
                if int(elapsed) % 30 == 0 and elapsed > 0:
                    print(f"📊 Progress: {elapsed:.0f}s - Messages: {message_count}, Events: {event_count}")
                
                # Wait for next iteration
                iteration_time = time.time() - iteration_start
                sleep_time = max(0, interval_seconds - iteration_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            print("\n⏹️  Simulation stopped by user")
        
        finally:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
        
        total_time = time.time() - start_time
        print(f"\n✅ Simulation completed:")
        print(f"   Total time: {total_time:.1f} seconds")
        print(f"   Messages sent: {message_count}")
        print(f"   Events sent: {event_count}")
        print(f"   Average rate: {message_count/total_time:.1f} messages/second")

def main():
    parser = argparse.ArgumentParser(description='Generate sample telemetry data')
    parser.add_argument('--devices', type=int, default=10, help='Number of devices to simulate')
    parser.add_argument('--duration', type=int, default=300, help='Simulation duration in seconds')
    parser.add_argument('--interval', type=float, default=2.0, help='Message interval in seconds')
    parser.add_argument('--mqtt-host', default='localhost', help='MQTT broker host')
    parser.add_argument('--mqtt-port', type=int, default=1883, help='MQTT broker port')
    parser.add_argument('--api-url', default='http://localhost:5000', help='API server URL')
    parser.add_argument('--use-api', action='store_true', help='Send data via API instead of MQTT')
    parser.add_argument('--output-file', help='Save generated data to JSON file')
    
    args = parser.parse_args()
    
    generator = TelemetryGenerator(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        api_base_url=args.api_url
    )
    
    if args.output_file:
        # Generate data and save to file
        print(f"📝 Generating sample data to {args.output_file}")
        
        data = []
        prev_speeds = [0.0] * args.devices
        
        for time_offset in range(0, args.duration, int(args.interval)):
            for device_index in range(args.devices):
                message, current_speed = generator.generate_telemetry_message(
                    device_index, time_offset, prev_speeds[device_index]
                )
                prev_speeds[device_index] = current_speed
                data.append(message)
                
                # Add some events
                if random.random() < 0.05:
                    event = generator.generate_harsh_driving_event(device_index)
                    data.append(event)
        
        with open(args.output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Generated {len(data)} records")
    else:
        # Run live simulation
        generator.run_simulation(
            num_devices=args.devices,
            duration_seconds=args.duration,
            interval_seconds=args.interval,
            use_mqtt=not args.use_api,
            use_api=args.use_api
        )

if __name__ == "__main__":
    main()