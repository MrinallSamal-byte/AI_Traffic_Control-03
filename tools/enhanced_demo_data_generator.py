#!/usr/bin/env python3
"""
Enhanced Demo Data Generator for Smart Transportation System
Generates realistic telemetry data, events, and scenarios
"""

import json
import random
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import paho.mqtt.client as mqtt
import requests
import threading
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleSimulator:
    """Simulates a single vehicle with realistic behavior"""
    
    def __init__(self, device_id: str, start_location: Dict[str, float]):
        self.device_id = device_id
        self.location = start_location.copy()
        self.speed = random.uniform(30, 80)  # km/h
        self.heading = random.uniform(0, 360)  # degrees
        self.fuel_level = random.uniform(20, 100)  # percentage
        self.vehicle_type = random.choice(['car', 'truck', 'motorcycle', 'bus'])
        
        # Driving behavior profile
        self.aggression_level = random.uniform(0, 1)  # 0 = calm, 1 = aggressive
        self.eco_driving = random.choice([True, False])
        
        # State tracking
        self.last_update = datetime.utcnow()
        self.trip_distance = 0
        self.events_generated = []
        
    def update_position(self, time_delta_seconds: float):
        """Update vehicle position based on speed and heading"""
        # Convert speed from km/h to degrees per second (rough approximation)
        speed_deg_per_sec = (self.speed / 3600) * (1 / 111)  # 1 degree ≈ 111 km
        
        # Update position
        lat_change = speed_deg_per_sec * time_delta_seconds * math.cos(math.radians(self.heading))
        lon_change = speed_deg_per_sec * time_delta_seconds * math.sin(math.radians(self.heading))
        
        self.location['lat'] += lat_change
        self.location['lon'] += lon_change
        
        # Keep within reasonable bounds (around Bhubaneswar, India)
        self.location['lat'] = max(20.25, min(20.35, self.location['lat']))
        self.location['lon'] = max(85.80, min(85.90, self.location['lon']))
        
        # Update trip distance
        distance_km = self.speed * (time_delta_seconds / 3600)
        self.trip_distance += distance_km
        
        # Consume fuel
        fuel_consumption = distance_km * random.uniform(0.05, 0.15)  # L/km
        self.fuel_level = max(0, self.fuel_level - fuel_consumption)
    
    def update_driving_behavior(self):
        """Update speed and heading based on driving behavior"""
        # Random speed variations
        if self.aggression_level > 0.7:
            # Aggressive driver
            speed_change = random.uniform(-10, 15)
            self.speed = max(20, min(120, self.speed + speed_change))
        elif self.eco_driving:
            # Eco driver
            speed_change = random.uniform(-5, 5)
            self.speed = max(30, min(70, self.speed + speed_change))
        else:
            # Normal driver
            speed_change = random.uniform(-8, 8)
            self.speed = max(25, min(100, self.speed + speed_change))
        
        # Random heading changes (turns)
        if random.random() < 0.1:  # 10% chance of turning
            heading_change = random.uniform(-45, 45)
            self.heading = (self.heading + heading_change) % 360
    
    def generate_telemetry(self) -> Dict[str, Any]:
        """Generate realistic telemetry data"""
        now = datetime.utcnow()
        time_delta = (now - self.last_update).total_seconds()
        
        # Update vehicle state
        self.update_position(time_delta)
        self.update_driving_behavior()
        
        # Generate acceleration based on driving behavior
        if self.aggression_level > 0.7:
            accel_x = random.uniform(-12, 12)  # Harsh braking/acceleration
            accel_y = random.uniform(-8, 8)    # Sharp turns
        else:
            accel_x = random.uniform(-4, 4)    # Normal acceleration
            accel_y = random.uniform(-3, 3)    # Gentle turns
        
        accel_z = random.uniform(9.5, 10.2)  # Gravity + vehicle dynamics
        
        # Generate engine data
        rpm = max(800, min(6000, self.speed * 50 + random.uniform(-200, 200)))
        engine_temp = random.uniform(80, 95) if self.speed > 60 else random.uniform(70, 85)
        
        # Generate diagnostics
        error_codes = []
        if random.random() < 0.05:  # 5% chance of error
            error_codes = [random.choice(['P0001', 'P0002', 'P0171', 'P0300'])]
        
        telemetry = {
            "deviceId": self.device_id,
            "timestamp": now.isoformat() + 'Z',
            "location": {
                "lat": round(self.location['lat'], 6),
                "lon": round(self.location['lon'], 6),
                "altitude": random.uniform(50, 150)
            },
            "speedKmph": round(self.speed, 1),
            "acceleration": {
                "x": round(accel_x, 2),
                "y": round(accel_y, 2),
                "z": round(accel_z, 2)
            },
            "fuelLevel": round(self.fuel_level, 1),
            "heading": round(self.heading, 1),
            "engineData": {
                "rpm": round(rpm),
                "engineTemp": round(engine_temp, 1),
                "throttlePosition": random.uniform(0, 100),
                "brakePosition": random.uniform(0, 20) if accel_x < -5 else 0
            },
            "diagnostics": {
                "errorCodes": error_codes,
                "batteryVoltage": random.uniform(12.0, 14.5),
                "oilPressure": random.uniform(20, 60)
            },
            "gyroscope": {
                "x": random.uniform(-10, 10),
                "y": random.uniform(-10, 10),
                "z": random.uniform(-5, 5)
            },
            "vehicleType": self.vehicle_type,
            "driverBehavior": {
                "seatbeltEngaged": random.choice([True, False]),
                "phoneUsage": random.random() < 0.1,  # 10% chance
                "drowsinessLevel": random.uniform(0, 3) if random.random() < 0.2 else 0
            }
        }
        
        self.last_update = now
        return telemetry
    
    def should_generate_event(self) -> bool:
        """Determine if vehicle should generate an event"""
        # Higher chance for aggressive drivers
        base_chance = 0.02 + (self.aggression_level * 0.08)  # 2-10% chance
        return random.random() < base_chance
    
    def generate_event(self) -> Dict[str, Any]:
        """Generate a driving event"""
        event_types = ['HARSH_BRAKE', 'HARSH_ACCEL', 'SHARP_TURN', 'SPEEDING', 'IDLE_TIME']
        
        # Weight event types based on driving behavior
        if self.aggression_level > 0.7:
            event_type = random.choice(['HARSH_BRAKE', 'HARSH_ACCEL', 'SHARP_TURN', 'SPEEDING'])
        else:
            event_type = random.choice(['IDLE_TIME', 'SPEEDING'])
        
        event = {
            "deviceId": self.device_id,
            "eventType": event_type,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "location": {
                "lat": round(self.location['lat'], 6),
                "lon": round(self.location['lon'], 6)
            },
            "speedBefore": round(self.speed, 1),
            "speedAfter": round(max(0, self.speed + random.uniform(-20, 10)), 1)
        }
        
        # Add event-specific data
        if event_type in ['HARSH_BRAKE', 'HARSH_ACCEL']:
            event["accelPeak"] = random.uniform(8, 15)
        elif event_type == 'SHARP_TURN':
            event["lateralAccel"] = random.uniform(6, 12)
        elif event_type == 'SPEEDING':
            event["speedLimit"] = 50
            event["excessSpeed"] = max(0, self.speed - 50)
        
        self.events_generated.append(event)
        return event

class DemoDataGenerator:
    """Main demo data generator"""
    
    def __init__(self, mqtt_host='localhost', mqtt_port=1883, api_base_url='http://localhost:5000'):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.api_base_url = api_base_url
        self.mqtt_client = None
        self.vehicles = {}
        self.running = False
        
    def setup_mqtt(self):
        """Setup MQTT client"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"✓ Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def create_vehicles(self, count: int):
        """Create vehicle simulators"""
        # Define starting locations around Bhubaneswar
        base_locations = [
            {"lat": 20.2961, "lon": 85.8245},  # City center
            {"lat": 20.3000, "lon": 85.8300},  # North area
            {"lat": 20.2900, "lon": 85.8200},  # South area
            {"lat": 20.2950, "lon": 85.8350},  # East area
            {"lat": 20.2980, "lon": 85.8150},  # West area
        ]
        
        for i in range(count):
            device_id = f"DEMO_DEVICE_{i+1:03d}"
            start_location = random.choice(base_locations).copy()
            
            # Add some random offset
            start_location['lat'] += random.uniform(-0.01, 0.01)
            start_location['lon'] += random.uniform(-0.01, 0.01)
            
            vehicle = VehicleSimulator(device_id, start_location)
            self.vehicles[device_id] = vehicle
            
        logger.info(f"✓ Created {count} vehicle simulators")
    
    def publish_telemetry(self, vehicle: VehicleSimulator):
        """Publish telemetry data via MQTT"""
        telemetry = vehicle.generate_telemetry()
        topic = f"/org/demo/device/{vehicle.device_id}/telemetry"
        
        try:
            self.mqtt_client.publish(topic, json.dumps(telemetry))
            logger.debug(f"📡 Published telemetry for {vehicle.device_id}")
        except Exception as e:
            logger.error(f"Failed to publish telemetry for {vehicle.device_id}: {e}")
    
    def publish_event(self, vehicle: VehicleSimulator):
        """Publish event data via MQTT"""
        event = vehicle.generate_event()
        topic = f"/org/demo/device/{vehicle.device_id}/events"
        
        try:
            self.mqtt_client.publish(topic, json.dumps(event))
            logger.info(f"🚨 Published {event['eventType']} event for {vehicle.device_id}")
        except Exception as e:
            logger.error(f"Failed to publish event for {vehicle.device_id}: {e}")
    
    def trigger_toll_event(self, vehicle: VehicleSimulator):
        """Trigger a toll event via API"""
        toll_data = {
            "device_id": vehicle.device_id,
            "gantry_id": f"GANTRY_{random.randint(1, 5):03d}",
            "location": vehicle.location,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "vehicle_type": vehicle.vehicle_type
        }
        
        try:
            response = requests.post(
                f"{self.api_base_url}/toll/charge",
                json=toll_data,
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"💰 Toll charged for {vehicle.device_id}: {result.get('amount', 0)} ETH")
            else:
                logger.warning(f"Toll charge failed for {vehicle.device_id}: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to trigger toll event for {vehicle.device_id}: {e}")
    
    def run_simulation(self, duration_minutes: int = 10, telemetry_interval: float = 2.0):
        """Run the simulation for specified duration"""
        if not self.mqtt_client:
            logger.error("MQTT client not connected")
            return
        
        if not self.vehicles:
            logger.error("No vehicles created")
            return
        
        logger.info(f"🚀 Starting simulation for {duration_minutes} minutes...")
        logger.info(f"📊 Vehicles: {len(self.vehicles)}, Telemetry interval: {telemetry_interval}s")
        
        self.running = True
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        iteration = 0
        
        while self.running and time.time() < end_time:
            iteration += 1
            
            for vehicle in self.vehicles.values():
                # Always publish telemetry
                self.publish_telemetry(vehicle)
                
                # Occasionally generate events
                if vehicle.should_generate_event():
                    self.publish_event(vehicle)
                
                # Occasionally trigger toll events
                if random.random() < 0.01:  # 1% chance per iteration
                    self.trigger_toll_event(vehicle)
            
            # Log progress
            if iteration % 10 == 0:
                elapsed = time.time() - start_time
                remaining = end_time - time.time()
                logger.info(f"⏱️  Iteration {iteration}, Elapsed: {elapsed:.1f}s, Remaining: {remaining:.1f}s")
            
            time.sleep(telemetry_interval)
        
        logger.info("✅ Simulation completed")
        self.print_simulation_summary()
    
    def print_simulation_summary(self):
        """Print simulation summary"""
        logger.info("\n📈 Simulation Summary:")
        logger.info("-" * 50)
        
        total_events = sum(len(v.events_generated) for v in self.vehicles.values())
        total_distance = sum(v.trip_distance for v in self.vehicles.values())
        
        logger.info(f"Vehicles simulated: {len(self.vehicles)}")
        logger.info(f"Total events generated: {total_events}")
        logger.info(f"Total distance traveled: {total_distance:.1f} km")
        
        # Event breakdown
        event_types = {}
        for vehicle in self.vehicles.values():
            for event in vehicle.events_generated:
                event_type = event['eventType']
                event_types[event_type] = event_types.get(event_type, 0) + 1
        
        if event_types:
            logger.info("\nEvent breakdown:")
            for event_type, count in event_types.items():
                logger.info(f"  {event_type}: {count}")
        
        logger.info("-" * 50)
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        logger.info("🛑 Simulation stopped")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Enhanced Demo Data Generator')
    parser.add_argument('--vehicles', type=int, default=5, help='Number of vehicles to simulate')
    parser.add_argument('--duration', type=int, default=10, help='Simulation duration in minutes')
    parser.add_argument('--interval', type=float, default=2.0, help='Telemetry interval in seconds')
    parser.add_argument('--mqtt-host', default='localhost', help='MQTT broker host')
    parser.add_argument('--mqtt-port', type=int, default=1883, help='MQTT broker port')
    parser.add_argument('--api-url', default='http://localhost:5000', help='API base URL')
    parser.add_argument('--scenario', choices=['normal', 'aggressive', 'eco'], default='normal',
                       help='Driving scenario to simulate')
    
    args = parser.parse_args()
    
    # Create generator
    generator = DemoDataGenerator(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        api_base_url=args.api_url
    )
    
    try:
        # Setup MQTT connection
        if not generator.setup_mqtt():
            return 1
        
        # Create vehicles
        generator.create_vehicles(args.vehicles)
        
        # Adjust vehicle behavior based on scenario
        if args.scenario == 'aggressive':
            for vehicle in generator.vehicles.values():
                vehicle.aggression_level = random.uniform(0.7, 1.0)
                vehicle.eco_driving = False
        elif args.scenario == 'eco':
            for vehicle in generator.vehicles.values():
                vehicle.aggression_level = random.uniform(0.0, 0.3)
                vehicle.eco_driving = True
        
        # Run simulation
        generator.run_simulation(args.duration, args.interval)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nSimulation interrupted by user")
        generator.stop_simulation()
        return 0
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return 1
    finally:
        generator.stop_simulation()

if __name__ == "__main__":
    exit(main())