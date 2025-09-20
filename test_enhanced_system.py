#!/usr/bin/env python3
"""
Enhanced System Integration Test
Tests all components working together
"""

import requests
import json
import time
import threading
from datetime import datetime
import socketio
import sys

class EnhancedSystemTest:
    def __init__(self):
        self.base_urls = {
            'api': 'http://localhost:5000',
            'ml': 'http://localhost:5001', 
            'blockchain': 'http://localhost:5002',
            'websocket': 'http://localhost:5003',
            'stream': 'http://localhost:5004'
        }
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
    
    def get_auth_token(self):
        """Get authentication token"""
        try:
            response = requests.post(f"{self.base_urls['api']}/auth/login", json={
                "username": "admin",
                "password": "password"
            }, timeout=5)
            
            if response.status_code == 200:
                self.auth_token = response.json()["access_token"]
                self.log_test("Authentication", True, "Token obtained")
                return True
            else:
                self.log_test("Authentication", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Authentication", False, str(e))
            return False
    
    def test_health_endpoints(self):
        """Test all health endpoints"""
        print("\n🏥 Testing Health Endpoints...")
        
        for service, url in self.base_urls.items():
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    self.log_test(f"Health - {service}", True, f"Status: {status}")
                else:
                    self.log_test(f"Health - {service}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"Health - {service}", False, str(e))
    
    def test_ml_inference(self):
        """Test ML inference endpoint"""
        print("\n🤖 Testing ML Inference...")
        
        test_data = {
            "device_id": "TEST_ML_001",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "speed": 75.0,
            "accel_x": 2.5,
            "accel_y": -1.2,
            "accel_z": 9.8,
            "jerk": 3.8,
            "yaw": 12.0
        }
        
        try:
            response = requests.post(
                f"{self.base_urls['ml']}/predict",
                json=test_data,
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                score = result.get('score', 0)
                alert = result.get('alert', 'UNKNOWN')
                model = result.get('model', 'unknown')
                
                # Validate response structure
                required_fields = ['score', 'model', 'alert', 'confidence']
                missing_fields = [f for f in required_fields if f not in result]
                
                if missing_fields:
                    self.log_test("ML Inference", False, f"Missing fields: {missing_fields}")
                elif not (0 <= score <= 100):
                    self.log_test("ML Inference", False, f"Invalid score: {score}")
                elif alert not in ['NORMAL', 'MEDIUM_RISK', 'HIGH_RISK']:
                    self.log_test("ML Inference", False, f"Invalid alert: {alert}")
                else:
                    self.log_test("ML Inference", True, f"Score: {score:.1f}, Alert: {alert}, Model: {model}")
            else:
                self.log_test("ML Inference", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("ML Inference", False, str(e))
    
    def test_toll_charging(self):
        """Test toll charging flow"""
        print("\n💰 Testing Toll Charging...")
        
        toll_data = {
            "device_id": "TEST_TOLL_001",
            "gantry_id": 1,
            "location": {"lat": 20.2961, "lon": 85.8245},
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "vehicle_type": "car"
        }
        
        try:
            response = requests.post(
                f"{self.base_urls['api']}/toll/charge",
                json=toll_data,
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                amount = result.get('amount', 0)
                toll_id = result.get('toll_id')
                tx_hash = result.get('tx_hash')
                
                if amount == 0.05 and toll_id and tx_hash:
                    self.log_test("Toll Charging", True, f"Amount: ${amount}, ID: {toll_id}")
                else:
                    self.log_test("Toll Charging", False, f"Invalid response: {result}")
            else:
                self.log_test("Toll Charging", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Toll Charging", False, str(e))
    
    def test_websocket_connection(self):
        """Test WebSocket real-time updates"""
        print("\n🔌 Testing WebSocket Connection...")
        
        messages_received = []
        connection_success = False
        
        def on_connect():
            nonlocal connection_success
            connection_success = True
        
        def on_telemetry_update(data):
            messages_received.append(('telemetry', data))
        
        def on_event_update(data):
            messages_received.append(('event', data))
        
        def on_toll_update(data):
            messages_received.append(('toll', data))
        
        try:
            sio = socketio.SimpleClient()
            sio.connect(self.base_urls['websocket'])
            
            sio.on('connect', on_connect)
            sio.on('telemetry_update', on_telemetry_update)
            sio.on('event_update', on_event_update)
            sio.on('toll_update', on_toll_update)
            
            # Wait for connection
            time.sleep(2)
            
            if connection_success:
                # Wait for some messages (demo data should be flowing)
                time.sleep(5)
                
                if messages_received:
                    message_types = set(msg[0] for msg in messages_received)
                    self.log_test("WebSocket Connection", True, 
                                f"Received {len(messages_received)} messages: {message_types}")
                else:
                    self.log_test("WebSocket Connection", True, "Connected but no demo data")
            else:
                self.log_test("WebSocket Connection", False, "Failed to connect")
            
            sio.disconnect()
            
        except Exception as e:
            self.log_test("WebSocket Connection", False, str(e))
    
    def test_model_management(self):
        """Test ML model management"""
        print("\n🔧 Testing Model Management...")
        
        try:
            # Get model info
            response = requests.get(f"{self.base_urls['ml']}/model/info", timeout=5)
            if response.status_code == 200:
                data = response.json()
                version = data.get('version')
                loaded = data.get('loaded', False)
                
                if loaded and version:
                    self.log_test("Model Info", True, f"Version: {version}, Loaded: {loaded}")
                else:
                    self.log_test("Model Info", False, f"Model not properly loaded: {data}")
            else:
                self.log_test("Model Info", False, f"HTTP {response.status_code}")
            
            # Test model reload
            response = requests.post(
                f"{self.base_urls['ml']}/model/reload",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'reloaded':
                    self.log_test("Model Reload", True, f"New version: {data.get('version')}")
                else:
                    self.log_test("Model Reload", False, f"Unexpected response: {data}")
            else:
                self.log_test("Model Reload", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Model Management", False, str(e))
    
    def test_metrics_collection(self):
        """Test metrics collection"""
        print("\n📊 Testing Metrics Collection...")
        
        try:
            # Make some requests to generate metrics
            requests.get(f"{self.base_urls['api']}/health")
            requests.get(f"{self.base_urls['ml']}/health")
            
            # Get metrics
            response = requests.get(f"{self.base_urls['api']}/metrics", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                required_metrics = ['request_count', 'error_count', 'avg_response_time']
                missing_metrics = [m for m in required_metrics if m not in data]
                
                if missing_metrics:
                    self.log_test("Metrics Collection", False, f"Missing: {missing_metrics}")
                else:
                    total_requests = sum(data['request_count'].values())
                    self.log_test("Metrics Collection", True, f"Total requests: {total_requests}")
            else:
                self.log_test("Metrics Collection", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Metrics Collection", False, str(e))
    
    def test_authentication_security(self):
        """Test authentication requirements"""
        print("\n🔐 Testing Authentication Security...")
        
        protected_endpoints = [
            ("POST", f"{self.base_urls['api']}/driver_score", {}),
            ("POST", f"{self.base_urls['api']}/toll/charge", {}),
            ("POST", f"{self.base_urls['ml']}/predict", {}),
            ("POST", f"{self.base_urls['ml']}/model/reload", {})
        ]
        
        success_count = 0
        for method, url, data in protected_endpoints:
            try:
                if method == "POST":
                    response = requests.post(url, json=data, timeout=5)
                else:
                    response = requests.get(url, timeout=5)
                
                if response.status_code == 401:
                    success_count += 1
                else:
                    print(f"  ⚠️  {url} returned {response.status_code} (expected 401)")
            except Exception as e:
                print(f"  ❌ {url} error: {e}")
        
        if success_count == len(protected_endpoints):
            self.log_test("Authentication Security", True, "All endpoints properly protected")
        else:
            self.log_test("Authentication Security", False, 
                         f"Only {success_count}/{len(protected_endpoints)} endpoints protected")
    
    def test_end_to_end_flow(self):
        """Test complete end-to-end flow"""
        print("\n🔄 Testing End-to-End Flow...")
        
        try:
            # 1. ML Inference
            ml_data = {
                "device_id": "E2E_TEST_001",
                "speed": 85.0,
                "accel_x": 4.0,
                "accel_y": -2.0,
                "accel_z": 9.8,
                "jerk": 5.0,
                "yaw": 20.0
            }
            
            ml_response = requests.post(
                f"{self.base_urls['ml']}/predict",
                json=ml_data,
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=10
            )
            
            if ml_response.status_code != 200:
                self.log_test("E2E Flow", False, "ML inference failed")
                return
            
            ml_result = ml_response.json()
            
            # 2. Toll Charging
            toll_data = {
                "device_id": "E2E_TEST_001",
                "gantry_id": 2,
                "location": {"lat": 20.3000, "lon": 85.8300},
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "vehicle_type": "car"
            }
            
            toll_response = requests.post(
                f"{self.base_urls['api']}/toll/charge",
                json=toll_data,
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=15
            )
            
            if toll_response.status_code != 200:
                self.log_test("E2E Flow", False, "Toll charging failed")
                return
            
            toll_result = toll_response.json()
            
            # 3. Verify results
            if (ml_result.get('score') and 
                ml_result.get('alert') and
                toll_result.get('toll_id') and
                toll_result.get('amount') == 0.05):
                
                self.log_test("E2E Flow", True, 
                             f"ML Score: {ml_result['score']:.1f}, "
                             f"Alert: {ml_result['alert']}, "
                             f"Toll: ${toll_result['amount']}")
            else:
                self.log_test("E2E Flow", False, "Invalid response data")
                
        except Exception as e:
            self.log_test("E2E Flow", False, str(e))
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🧪 Enhanced System Integration Tests")
        print("=" * 50)
        
        # Get authentication token first
        if not self.get_auth_token():
            print("❌ Cannot proceed without authentication")
            return False
        
        # Run all tests
        self.test_health_endpoints()
        self.test_ml_inference()
        self.test_toll_charging()
        self.test_websocket_connection()
        self.test_model_management()
        self.test_metrics_collection()
        self.test_authentication_security()
        self.test_end_to_end_flow()
        
        # Summary
        print("\n" + "=" * 50)
        print("📋 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for r in self.test_results if r['success'])
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {total - passed}")
        print(f"📊 Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! System is working correctly.")
            return True
        else:
            print(f"\n⚠️  {total - passed} tests failed. Check the logs above.")
            
            # Show failed tests
            failed_tests = [r for r in self.test_results if not r['success']]
            if failed_tests:
                print("\n❌ Failed Tests:")
                for test in failed_tests:
                    print(f"  • {test['test']}: {test['message']}")
            
            return False

if __name__ == "__main__":
    print("🚀 Starting Enhanced System Integration Tests...")
    print("Make sure the system is running: python start_enhanced_system.py")
    print()
    
    # Wait a moment for user to confirm
    try:
        input("Press Enter to continue or Ctrl+C to cancel...")
    except KeyboardInterrupt:
        print("\n❌ Tests cancelled")
        sys.exit(1)
    
    tester = EnhancedSystemTest()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)