#!/usr/bin/env python3
"""
Smart Transportation System - Vehicle Edge Simulator
Simulates OBU telemetry data and publishes to MQTT broker
"""

import json
import time
import uuid
import random
import math
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
import requests
import argparse

class VehicleSimulator:
    def __init__(self, device_id=None, broker_host="localhost", broker_port=1883, mode="mqtt", api_url="http://localhost:5000"):
        self.device_id = device_id or f"OBU-{str(uuid.uuid4())[:8]}"
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.mode = mode
        self.api_url = api_url
        self.client = mqtt.Client() if mode == "mqtt" else None
        self.running = False
        
        # Vehicle state
        self.latitude = 20.2961 + random.uniform(-0.01, 0.01)
        self.longitude = 85.8245 + random.uniform(-0.01, 0.01)
        self.speed = 0.0
        self.heading = random.uniform(0, 360)
        self.rpm = 800
        self.throttle = 0.0
        self.brake = 0.0
        self.battery_voltage = 12.1
        
        # Movement parameters
        self.target_speed = 50.0
        self.route_points = self._generate_route()
        self.current_route_index = 0
        
        # Setup MQTT callbacks
        if self.client:
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
        
    def _generate_route(self):
        """Generate a simple route with waypoints"""
        base_lat, base_lon = self.latitude, self.longitude
        return [
            (base_lat, base_lon),
            (base_lat + 0.005, base_lon + 0.003),
            (base_lat + 0.008, base_lon + 0.008),
            (base_lat + 0.003, base_lon + 0.012),
            (base_lat - 0.002, base_lon + 0.015),
        ]
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ Device {self.device_id} connected to MQTT broker")
        else:
            print(f"✗ Failed to connect: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        print(f"✗ Device {self.device_id} disconnected from MQTT broker")
    
    def connect(self):
        """Connect to MQTT broker or test HTTP endpoint"""
        if self.mode == "http":
            try:
                response = requests.get(f"{self.api_url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"✓ Device {self.device_id} connected to HTTP API")
                    return True
                else:
                    print(f"✗ HTTP API not available: {response.status_code}")
                    return False
            except Exception as e:
                print(f"✗ HTTP connection failed: {e}")
                return False
        else:
            try:
                self.client.connect(self.broker_host, self.broker_port, 60)
                self.client.loop_start()
                return True
            except Exception as e:
                print(f"✗ MQTT connection failed: {e}")
                return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
    
    def _update_position(self):
        """Update vehicle position along route"""
        if self.current_route_index < len(self.route_points) - 1:
            current = self.route_points[self.current_route_index]
            target = self.route_points[self.current_route_index + 1]
            
            # Calculate direction to target
            dlat = target[0] - current[0]
            dlon = target[1] - current[1]
            distance = math.sqrt(dlat**2 + dlon**2)
            
            if distance > 0.0001:  # Not at target yet
                # Move towards target
                speed_ms = self.speed / 3.6  # km/h to m/s
                move_distance = speed_ms * 0.00001  # Approximate degrees per meter
                
                self.latitude += (dlat / distance) * move_distance
                self.longitude += (dlon / distance) * move_distance
                self.heading = math.degrees(math.atan2(dlon, dlat))
            else:
                # Reached waypoint, move to next
                self.current_route_index += 1
                if self.current_route_index >= len(self.route_points):
                    self.current_route_index = 0  # Loop back
    
    def _simulate_driving_behavior(self):
        """Simulate realistic driving behavior"""
        # Speed variation
        speed_diff = self.target_speed - self.speed
        if abs(speed_diff) > 1:
            self.speed += speed_diff * 0.1
        else:
            self.speed += random.uniform(-2, 2)
        
        self.speed = max(0, min(120, self.speed))  # Clamp speed
        
        # RPM based on speed
        self.rpm = 800 + (self.speed * 30)
        
        # Throttle and brake
        if speed_diff > 5:
            self.throttle = min(100, self.throttle + 10)
            self.brake = 0
        elif speed_diff < -5:
            self.brake = min(100, self.brake + 15)
            self.throttle = 0
        else:
            self.throttle = max(0, self.throttle - 5)
            self.brake = max(0, self.brake - 10)
        
        # Battery voltage variation
        self.battery_voltage += random.uniform(-0.05, 0.05)
        self.battery_voltage = max(11.5, min(12.8, self.battery_voltage))
    
    def _generate_telemetry(self):
        """Generate telemetry payload"""
        # Simulate IMU data
        accel_x = random.uniform(-0.5, 0.5)
        accel_y = random.uniform(-0.3, 0.3)
        accel_z = 9.78 + random.uniform(-0.1, 0.1)
        
        # Add noise for harsh events
        if random.random() < 0.02:  # 2% chance of harsh event
            if random.random() < 0.5:
                accel_x = random.uniform(-8, -5)  # Harsh brake
            else:
                accel_x = random.uniform(5, 8)   # Harsh acceleration
        
        # Calculate jerk (rate of change of acceleration)
        jerk = random.uniform(-0.5, 0.5)
        if abs(accel_x) > 3:  # High acceleration events have higher jerk
            jerk = random.uniform(-2, 2)
        
        # Generate yaw rate
        yaw = random.uniform(-0.1, 0.1)
        
        if self.mode == "http":
            # Simplified format for HTTP API
            return {
                "device_id": self.device_id,
                "timestamp": int(datetime.utcnow().timestamp()),
                "speed": round(self.speed, 1),
                "accel_x": round(accel_x, 3),
                "accel_y": round(accel_y, 3),
                "accel_z": round(accel_z, 3),
                "jerk": round(jerk, 3),
                "yaw": round(yaw, 4)
            }
        else:
            # Full MQTT format
            return {
                "deviceId": self.device_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "location": {
                    "lat": round(self.latitude, 8),
                    "lon": round(self.longitude, 8),
                    "hdop": round(random.uniform(0.5, 1.5), 1),
                    "alt": round(random.uniform(20, 30), 1)
                },
                "speedKmph": round(self.speed, 1),
                "heading": round(self.heading, 1),
                "imu": {
                    "ax": round(accel_x, 3),
                    "ay": round(accel_y, 3),
                    "az": round(accel_z, 3),
                    "gx": round(random.uniform(-0.01, 0.01), 4),
                    "gy": round(random.uniform(-0.01, 0.01), 4),
                    "gz": round(random.uniform(-0.01, 0.01), 4)
                },
                "can": {
                    "rpm": int(self.rpm),
                    "throttle": round(self.throttle, 1),
                    "brake": round(self.brake, 1)
                },
                "batteryVoltage": round(self.battery_voltage, 2),
                "signature": "mock_signature_" + str(uuid.uuid4())[:16]
            }
    
    def _check_events(self, telemetry):
        """Check for driving events and publish them"""
        accel_x = telemetry["imu"]["ax"]
        
        if abs(accel_x) > 5:  # Harsh event threshold
            event_type = "HARSH_BRAKE" if accel_x < 0 else "HARSH_ACCEL"
            
            event = {
                "eventType": event_type,
                "timestamp": telemetry["timestamp"],
                "deviceId": self.device_id,
                "location": telemetry["location"],
                "speedBefore": telemetry["speedKmph"],
                "speedAfter": max(0, telemetry["speedKmph"] + accel_x),
                "accelPeak": accel_x
            }
            
            topic = f"/org/demo/device/{self.device_id}/events"
            self.client.publish(topic, json.dumps(event))
            print(f"🚨 Event: {event_type} at {telemetry['speedKmph']} km/h")
    
    def start_simulation(self, interval=1.0):
        """Start telemetry simulation"""
        self.running = True
        print(f"🚗 Starting simulation for device {self.device_id}")
        
        while self.running:
            try:
                # Update vehicle state
                self._update_position()
                self._simulate_driving_behavior()
                
                # Generate and publish telemetry
                telemetry = self._generate_telemetry()
                
                if self.mode == "http":
                    # Send via HTTP POST
                    try:
                        response = requests.post(
                            f"{self.api_url}/driver_score",
                            json=telemetry,
                            timeout=5
                        )
                        if response.status_code == 200:
                            result = response.json()
                            timestamp = datetime.utcnow().strftime('%H:%M:%S')
                            score = result.get('driver_score', 0)
                            model = result.get('model', 'unknown')
                            print(f"{timestamp} | {self.device_id} -> score={score:.2f} model={model}")
                        else:
                            print(f"❌ {self.device_id}: HTTP error {response.status_code}")
                    except Exception as e:
                        print(f"❌ {self.device_id}: HTTP request failed: {e}")
                else:
                    # Send via MQTT
                    topic = f"/org/demo/device/{self.device_id}/telemetry"
                    result = self.client.publish(topic, json.dumps(telemetry))
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        print(f"📡 {self.device_id}: Speed {telemetry['speedKmph']} km/h at ({telemetry['location']['lat']:.6f}, {telemetry['location']['lon']:.6f})")
                    
                    # Check for events (MQTT only)
                    self._check_events(telemetry)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print(f"\n🛑 Stopping simulation for {self.device_id}")
                break
            except Exception as e:
                print(f"✗ Error in simulation: {e}")
                time.sleep(1)

def simulate_multiple_vehicles(count=3, broker_host="localhost", mode="mqtt", api_url="http://localhost:5000"):
    """Simulate multiple vehicles"""
    simulators = []
    threads = []
    
    print(f"🚗 Starting {count} vehicle simulators in {mode} mode...")
    
    for i in range(count):
        sim = VehicleSimulator(broker_host=broker_host, mode=mode, api_url=api_url)
        if sim.connect():
            simulators.append(sim)
            
            # Start each simulator in a separate thread
            thread = threading.Thread(
                target=sim.start_simulation,
                args=(random.uniform(0.8, 1.2),)  # Vary intervals
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
            
            time.sleep(0.5)  # Stagger starts
    
    try:
        # Wait for all threads
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all simulators...")
        for sim in simulators:
            sim.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vehicle Edge Simulator")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--devices", type=int, default=3, help="Number of vehicles to simulate")
    parser.add_argument("--interval", type=float, default=1.0, help="Telemetry interval in seconds")
    parser.add_argument("--mode", choices=["mqtt", "http"], default="http", help="Communication mode")
    parser.add_argument("--api-url", default="http://localhost:5000", help="API server URL for HTTP mode")
    parser.add_argument("--device-id", help="Specific device ID (single vehicle mode)")
    
    args = parser.parse_args()
    
    if args.device_id:
        # Single vehicle mode
        sim = VehicleSimulator(
            device_id=args.device_id, 
            broker_host=args.broker, 
            mode=args.mode, 
            api_url=args.api_url
        )
        if sim.connect():
            sim.start_simulation(args.interval)
        sim.disconnect()
    else:
        # Multi-vehicle mode
        simulate_multiple_vehicles(
            args.devices, 
            args.broker, 
            args.mode, 
            args.api_url
        )