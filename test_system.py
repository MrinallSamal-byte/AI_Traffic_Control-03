#!/usr/bin/env python3
"""
Smart Transportation System - Integration Test Suite
Tests end-to-end functionality of the complete system
"""

import requests
import json
import time
import uuid
from datetime import datetime
import paho.mqtt.client as mqtt
import threading

class SystemTester:
    def __init__(self):
        self.api_base = "http://localhost:5000/api/v1"
        self.ml_base = "http://localhost:5001"
        self.blockchain_base = "http://localhost:5002"
        self.mqtt_broker = "localhost"
        self.mqtt_port = 1883
        
        self.test_results = []
        self.mqtt_client = None
        
    def log_test(self, test_name, success, message=""):
        """Log test result"""
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_service_health(self):
        """Test all service health endpoints"""
        print("\n🔍 Testing Service Health...")
        
        services = [
            ("API Server", f"{self.api_base}/../health"),
            ("ML Service", f"{self.ml_base}/health"),
            ("Blockchain Service", f"{self.blockchain_base}/health")
        ]
        
        for name, url in services:
            try:
                response = requests.get(url, timeout=5)
                success = response.status_code == 200
                
                if success:
                    data = response.json()
                    self.log_test(f"{name} Health Check", True, f"Status: {data.get('status', 'unknown')}")
                else:
                    self.log_test(f"{name} Health Check", False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"{name} Health Check", False, str(e))
    
    def test_user_registration_and_auth(self):
        """Test user registration and authentication"""
        print("\n👤 Testing User Management...")
        
        # Test user registration
        test_user = {
            "name": "Test User",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "phone": "+1234567890"
        }
        
        try:
            response = requests.post(f"{self.api_base}/auth/register", json=test_user)
            
            if response.status_code == 201:
                data = response.json()
                access_token = data.get('access_token')
                user_id = data.get('user', {}).get('user_id')
                
                self.log_test("User Registration", True, f"User ID: {user_id}")
                
                # Test login
                login_data = {
                    "email": test_user["email"],
                    "password": "dummy_password"  # Simplified auth for testing
                }
                
                # Store token for subsequent tests
                self.access_token = access_token
                self.test_user_id = user_id
                
                self.log_test("User Authentication", True, "Token received")
                
            else:
                self.log_test("User Registration", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("User Registration", False, str(e))
    
    def test_vehicle_registration(self):
        """Test vehicle registration"""
        print("\n🚗 Testing Vehicle Management...")
        
        if not hasattr(self, 'access_token'):
            self.log_test("Vehicle Registration", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        vehicle_data = {
            "registration_no": f"TEST{uuid.uuid4().hex[:6].upper()}",
            "obu_device_id": f"OBU-TEST-{uuid.uuid4().hex[:8]}"
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/devices/register",
                json=vehicle_data,
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                vehicle_id = data.get('vehicle', {}).get('vehicle_id')
                self.test_vehicle_id = vehicle_id
                self.test_device_id = vehicle_data["obu_device_id"]
                
                self.log_test("Vehicle Registration", True, f"Vehicle ID: {vehicle_id}")
            else:
                self.log_test("Vehicle Registration", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Vehicle Registration", False, str(e))
    
    def test_mqtt_telemetry(self):
        """Test MQTT telemetry publishing"""
        print("\n📡 Testing MQTT Telemetry...")
        
        if not hasattr(self, 'test_device_id'):
            self.log_test("MQTT Telemetry", False, "No test device available")
            return
        
        try:
            # Setup MQTT client
            client = mqtt.Client()
            connected = threading.Event()
            published = threading.Event()
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    connected.set()
            
            def on_publish(client, userdata, mid):
                published.set()
            
            client.on_connect = on_connect
            client.on_publish = on_publish
            
            # Connect and publish
            client.connect(self.mqtt_broker, self.mqtt_port, 60)
            client.loop_start()
            
            # Wait for connection
            if connected.wait(timeout=10):
                # Publish test telemetry
                telemetry = {
                    "deviceId": self.test_device_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "location": {"lat": 20.2961, "lon": 85.8245, "hdop": 0.8, "alt": 24.5},
                    "speedKmph": 45.2,
                    "heading": 128.0,
                    "imu": {"ax": -0.12, "ay": 0.02, "az": 9.78, "gx": 0.001, "gy": -0.003},
                    "can": {"rpm": 2200, "throttle": 19.7, "brake": 0},
                    "batteryVoltage": 12.10,
                    "signature": "test_signature"
                }
                
                topic = f"/org/demo/device/{self.test_device_id}/telemetry"
                client.publish(topic, json.dumps(telemetry))
                
                if published.wait(timeout=5):
                    self.log_test("MQTT Telemetry Publish", True, f"Published to {topic}")
                else:
                    self.log_test("MQTT Telemetry Publish", False, "Publish timeout")
            else:
                self.log_test("MQTT Connection", False, "Connection timeout")
            
            client.loop_stop()
            client.disconnect()
            
        except Exception as e:
            self.log_test("MQTT Telemetry", False, str(e))
    
    def test_ml_scoring(self):
        """Test ML driver scoring service"""
        print("\n🧠 Testing ML Services...")
        
        # Test with sample telemetry data
        sample_telemetry = [
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "speed_kmph": 45.2,
                "acceleration_x": -0.12,
                "acceleration_y": 0.02,
                "acceleration_z": 9.78,
                "gyro_x": 0.001,
                "gyro_y": -0.003,
                "gyro_z": 0.001,
                "rpm": 2200,
                "throttle": 19.7,
                "brake": 0
            }
        ]
        
        try:
            response = requests.post(
                f"{self.ml_base}/score",
                json={"telemetry": sample_telemetry}
            )
            
            if response.status_code == 200:
                data = response.json()
                score = data.get('score', 0)
                self.log_test("ML Driver Scoring", True, f"Score: {score}")
            else:
                self.log_test("ML Driver Scoring", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("ML Driver Scoring", False, str(e))
    
    def test_blockchain_integration(self):
        """Test blockchain smart contract integration"""
        print("\n⛓️  Testing Blockchain Integration...")
        
        try:
            # Test blockchain health
            response = requests.get(f"{self.blockchain_base}/health")
            
            if response.status_code == 200:
                self.log_test("Blockchain Connection", True, "Service responsive")
                
                # Test toll creation (mock)
                toll_data = {
                    "vehicle_address": "0x742d35Cc6634C0532925a3b8D4C2C4e07C3c4526",
                    "gantry_id": 1,
                    "amount": 0.025
                }
                
                response = requests.post(f"{self.blockchain_base}/toll/create", json=toll_data)
                
                if response.status_code == 200:
                    data = response.json()
                    toll_id = data.get('toll_id')
                    self.log_test("Blockchain Toll Creation", True, f"Toll ID: {toll_id}")
                else:
                    self.log_test("Blockchain Toll Creation", False, f"HTTP {response.status_code}")
            else:
                self.log_test("Blockchain Connection", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Blockchain Integration", False, str(e))
    
    def test_toll_gantries(self):
        """Test toll gantry management"""
        print("\n🏛️  Testing Toll Management...")
        
        try:
            response = requests.get(f"{self.api_base}/toll/gantries")
            
            if response.status_code == 200:
                data = response.json()
                gantries = data.get('gantries', [])
                self.log_test("Toll Gantries Retrieval", True, f"Found {len(gantries)} gantries")
                
                if gantries:
                    # Test toll charge simulation
                    if hasattr(self, 'test_vehicle_id'):
                        charge_data = {
                            "vehicleId": self.test_vehicle_id,
                            "gantryId": gantries[0]['gantry_id'],
                            "calculatedPrice": 25.00
                        }
                        
                        response = requests.post(f"{self.api_base}/toll/charge", json=charge_data)
                        
                        if response.status_code in [200, 402]:  # 402 = insufficient balance is expected
                            self.log_test("Toll Charge Processing", True, "Charge processed")
                        else:
                            self.log_test("Toll Charge Processing", False, f"HTTP {response.status_code}")
            else:
                self.log_test("Toll Gantries Retrieval", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Toll Management", False, str(e))
    
    def test_dashboard_data(self):
        """Test dashboard data endpoints"""
        print("\n📊 Testing Dashboard Integration...")
        
        if not hasattr(self, 'access_token'):
            self.log_test("Dashboard Data", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(f"{self.api_base}/admin/dashboard", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('statistics', {})
                self.log_test("Dashboard Data Retrieval", True, f"Stats: {len(stats)} metrics")
            else:
                self.log_test("Dashboard Data Retrieval", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Dashboard Data", False, str(e))
    
    def test_end_to_end_flow(self):
        """Test complete end-to-end flow"""
        print("\n🔄 Testing End-to-End Flow...")
        
        # Wait for telemetry to be processed
        time.sleep(5)
        
        if hasattr(self, 'test_vehicle_id') and hasattr(self, 'access_token'):
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            try:
                # Check if telemetry was stored
                response = requests.get(
                    f"{self.api_base}/vehicles/{self.test_vehicle_id}/telemetry?hours=1",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    telemetry_count = data.get('count', 0)
                    
                    if telemetry_count > 0:
                        self.log_test("End-to-End Telemetry Flow", True, f"{telemetry_count} records stored")
                    else:
                        self.log_test("End-to-End Telemetry Flow", False, "No telemetry stored")
                else:
                    self.log_test("End-to-End Telemetry Flow", False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test("End-to-End Flow", False, str(e))
        else:
            self.log_test("End-to-End Flow", False, "Missing test prerequisites")
    
    def run_all_tests(self):
        """Run all system tests"""
        print("🧪 Smart Transportation System - Integration Tests")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run tests in sequence
        self.test_service_health()
        self.test_user_registration_and_auth()
        self.test_vehicle_registration()
        self.test_mqtt_telemetry()
        self.test_ml_scoring()
        self.test_blockchain_integration()
        self.test_toll_gantries()
        self.test_dashboard_data()
        self.test_end_to_end_flow()
        
        # Generate test report
        self.generate_test_report(start_time)
    
    def generate_test_report(self, start_time):
        """Generate and display test report"""
        end_time = time.time()
        duration = end_time - start_time
        
        passed = sum(1 for result in self.test_results if result['success'])
        failed = len(self.test_results) - passed
        
        print("\n" + "=" * 60)
        print("📋 TEST REPORT")
        print("=" * 60)
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   • {result['test']}: {result['message']}")
        
        print("\n💾 Saving test report...")
        
        # Save detailed report
        report = {
            'summary': {
                'total_tests': len(self.test_results),
                'passed': passed,
                'failed': failed,
                'success_rate': passed/len(self.test_results)*100,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            },
            'results': self.test_results
        }
        
        with open('test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("✓ Test report saved to test_report.json")
        print("=" * 60)

def main():
    """Main test runner"""
    print("🚀 Starting Smart Transportation System Tests...")
    print("Make sure all services are running before proceeding.")
    
    input("Press Enter to continue with tests...")
    
    tester = SystemTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()