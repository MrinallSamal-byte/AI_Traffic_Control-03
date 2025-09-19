#!/usr/bin/env python3
"""
Stress Test - Simulate 10,000 vehicles for system load testing
"""

import json
import time
import uuid
import random
import threading
import argparse
from datetime import datetime
import paho.mqtt.client as mqtt
from concurrent.futures import ThreadPoolExecutor

class StressTestVehicle:
    def __init__(self, device_id, broker_host, broker_port):
        self.device_id = device_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client()
        self.running = False
        
        # Random starting position
        self.lat = 20.2961 + random.uniform(-0.1, 0.1)
        self.lon = 85.8245 + random.uniform(-0.1, 0.1)
        self.speed = random.uniform(30, 80)
        self.heading = random.uniform(0, 360)
        
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except:
            return False
    
    def generate_telemetry(self):
        """Generate minimal telemetry for stress testing"""
        # Update position slightly
        self.lat += random.uniform(-0.0001, 0.0001)
        self.lon += random.uniform(-0.0001, 0.0001)
        self.speed += random.uniform(-2, 2)
        self.speed = max(0, min(120, self.speed))
        
        return {
            "deviceId": self.device_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "location": {"lat": self.lat, "lon": self.lon},
            "speedKmph": self.speed,
            "heading": self.heading
        }
    
    def run_test(self, duration_seconds, interval):
        """Run stress test for specified duration"""
        self.running = True
        start_time = time.time()
        message_count = 0
        
        while self.running and (time.time() - start_time) < duration_seconds:
            telemetry = self.generate_telemetry()
            topic = f"/org/demo/device/{self.device_id}/telemetry"
            
            try:
                self.client.publish(topic, json.dumps(telemetry))
                message_count += 1
            except:
                pass
            
            time.sleep(interval)
        
        self.client.loop_stop()
        self.client.disconnect()
        return message_count

class StressTestManager:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.vehicles = []
        self.results = {}
        
    def create_vehicles(self, count):
        """Create stress test vehicles"""
        print(f"Creating {count} virtual vehicles...")
        
        for i in range(count):
            device_id = f"STRESS-{i:05d}"
            vehicle = StressTestVehicle(device_id, self.broker_host, self.broker_port)
            self.vehicles.append(vehicle)
            
            if (i + 1) % 1000 == 0:
                print(f"Created {i + 1}/{count} vehicles")
    
    def run_stress_test(self, duration_seconds=300, message_interval=1.0, max_workers=100):
        """Run stress test with multiple vehicles"""
        print(f"Starting stress test with {len(self.vehicles)} vehicles")
        print(f"Duration: {duration_seconds}s, Interval: {message_interval}s")
        
        start_time = time.time()
        
        def run_vehicle(vehicle):
            if vehicle.connect():
                return vehicle.run_test(duration_seconds, message_interval)
            return 0
        
        # Use ThreadPoolExecutor to manage connections
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(run_vehicle, vehicle) for vehicle in self.vehicles]
            
            # Monitor progress
            completed = 0
            total_messages = 0
            
            for future in futures:
                try:
                    messages = future.result(timeout=duration_seconds + 30)
                    total_messages += messages
                    completed += 1
                    
                    if completed % 100 == 0:
                        print(f"Completed: {completed}/{len(self.vehicles)} vehicles")
                        
                except Exception as e:
                    print(f"Vehicle failed: {e}")
        
        end_time = time.time()
        test_duration = end_time - start_time
        
        # Calculate statistics
        self.results = {
            'total_vehicles': len(self.vehicles),
            'test_duration': test_duration,
            'total_messages': total_messages,
            'messages_per_second': total_messages / test_duration,
            'vehicles_per_second': len(self.vehicles) / test_duration
        }
        
        self.print_results()
    
    def print_results(self):
        """Print test results"""
        print("\n" + "="*50)
        print("STRESS TEST RESULTS")
        print("="*50)
        print(f"Total Vehicles: {self.results['total_vehicles']:,}")
        print(f"Test Duration: {self.results['test_duration']:.2f} seconds")
        print(f"Total Messages: {self.results['total_messages']:,}")
        print(f"Messages/Second: {self.results['messages_per_second']:.2f}")
        print(f"Vehicles/Second: {self.results['vehicles_per_second']:.2f}")
        print("="*50)

def main():
    parser = argparse.ArgumentParser(description="Stress Test Tool")
    parser.add_argument("--vehicles", type=int, default=1000, help="Number of vehicles to simulate")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Message interval in seconds")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--workers", type=int, default=100, help="Max concurrent workers")
    
    args = parser.parse_args()
    
    # Validate vehicle count
    if args.vehicles > 10000:
        print("Warning: Testing with more than 10,000 vehicles may overwhelm the system")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            return
    
    manager = StressTestManager(args.broker)
    manager.create_vehicles(args.vehicles)
    manager.run_stress_test(args.duration, args.interval, args.workers)

if __name__ == "__main__":
    main()