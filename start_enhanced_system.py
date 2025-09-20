#!/usr/bin/env python3
"""
Enhanced System Startup Script
Starts all services with proper dependencies and health checks
"""

import subprocess
import time
import requests
import sys
import os
import threading
import signal
from pathlib import Path

class SystemManager:
    def __init__(self):
        self.processes = []
        self.services = {
            'blockchain': {'port': 5002, 'cmd': ['python', 'blockchain/blockchain_service.py']},
            'api_server': {'port': 5000, 'cmd': ['python', 'api_server/app.py']},
            'ml_services': {'port': 5001, 'cmd': ['python', 'ml_services/ml_api.py']},
            'stream_processor': {'port': 5004, 'cmd': ['python', 'stream_processor/processor.py']},
            'websocket_server': {'port': 5003, 'cmd': ['python', 'api_server/websocket_handler.py']}
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.shutdown_all()
        sys.exit(0)
    
    def check_dependencies(self):
        """Check if required dependencies are available"""
        print("🔍 Checking dependencies...")
        
        # Check Python packages
        required_packages = [
            'flask', 'paho-mqtt', 'redis', 'psycopg2', 'sklearn', 
            'web3', 'socketio', 'pydantic', 'geopy'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install -r requirements.txt")
            return False
        
        print("✅ All Python dependencies available")
        return True
    
    def train_baseline_model(self):
        """Train baseline ML model if not exists"""
        model_dir = Path("ml_services/models")
        if not any(model_dir.glob("driver_model_v*.pkl")):
            print("🤖 Training baseline ML model...")
            try:
                result = subprocess.run([
                    sys.executable, "ml_services/train_baseline_model.py"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print("✅ Baseline model trained successfully")
                else:
                    print(f"❌ Model training failed: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                print("❌ Model training timed out")
                return False
            except Exception as e:
                print(f"❌ Model training error: {e}")
                return False
        else:
            print("✅ ML model already exists")
        
        return True
    
    def start_service(self, name, config):
        """Start a single service"""
        print(f"🚀 Starting {name}...")
        
        try:
            process = subprocess.Popen(
                config['cmd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append((name, process))
            
            # Start log monitoring in background
            threading.Thread(
                target=self.monitor_service_logs,
                args=(name, process),
                daemon=True
            ).start()
            
            return process
            
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return None
    
    def monitor_service_logs(self, name, process):
        """Monitor service logs"""
        while process.poll() is None:
            try:
                line = process.stdout.readline()
                if line:
                    print(f"[{name}] {line.strip()}")
            except:
                break
    
    def wait_for_service(self, name, port, timeout=30):
        """Wait for service to be ready"""
        print(f"⏳ Waiting for {name} on port {port}...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=2)
                if response.status_code == 200:
                    print(f"✅ {name} is ready")
                    return True
            except:
                pass
            time.sleep(1)
        
        print(f"❌ {name} failed to start within {timeout}s")
        return False
    
    def start_all_services(self):
        """Start all services in proper order"""
        print("🚀 Starting Enhanced Smart Transportation System...")
        
        # Start services in dependency order
        service_order = ['blockchain', 'api_server', 'ml_services', 'websocket_server', 'stream_processor']
        
        for service_name in service_order:
            config = self.services[service_name]
            
            process = self.start_service(service_name, config)
            if not process:
                print(f"❌ Failed to start {service_name}")
                return False
            
            # Wait for service to be ready
            if not self.wait_for_service(service_name, config['port']):
                print(f"❌ {service_name} not responding")
                return False
            
            time.sleep(2)  # Brief pause between services
        
        return True
    
    def check_system_health(self):
        """Check health of all services"""
        print("\n🏥 System Health Check:")
        all_healthy = True
        
        for name, config in self.services.items():
            try:
                response = requests.get(f"http://localhost:{config['port']}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    print(f"  ✅ {name}: {status}")
                else:
                    print(f"  ❌ {name}: HTTP {response.status_code}")
                    all_healthy = False
            except Exception as e:
                print(f"  ❌ {name}: {str(e)}")
                all_healthy = False
        
        return all_healthy
    
    def start_demo_components(self):
        """Start demo components"""
        print("\n🎮 Starting demo components...")
        
        # Start device simulators
        print("🚗 Starting vehicle simulators...")
        simulator_process = subprocess.Popen([
            sys.executable, "device_simulator/simulator.py",
            "--devices", "3",
            "--mode", "mqtt"
        ])
        self.processes.append(("simulators", simulator_process))
        
        print("✅ Demo components started")
    
    def show_dashboard_info(self):
        """Show dashboard access information"""
        print("\n" + "="*60)
        print("🎯 SYSTEM READY!")
        print("="*60)
        print("📊 Dashboard: http://localhost:3000")
        print("   (Open dashboard/index.html in browser)")
        print("")
        print("🔗 API Endpoints:")
        print("   • API Server: http://localhost:5000")
        print("   • ML Services: http://localhost:5001")
        print("   • Blockchain: http://localhost:5002")
        print("   • WebSocket: http://localhost:5003")
        print("   • Stream Processor: http://localhost:5004")
        print("")
        print("🔐 Default Login:")
        print("   • Username: admin")
        print("   • Password: password")
        print("")
        print("🚗 Vehicle Simulators: 3 devices running")
        print("💰 Toll Gantries: 3 locations active")
        print("")
        print("Press Ctrl+C to stop all services")
        print("="*60)
    
    def shutdown_all(self):
        """Shutdown all services"""
        print("\n🛑 Shutting down all services...")
        
        for name, process in self.processes:
            try:
                print(f"  Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"  Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"  Error stopping {name}: {e}")
        
        print("✅ All services stopped")
    
    def run(self):
        """Main run method"""
        try:
            # Pre-flight checks
            if not self.check_dependencies():
                return False
            
            if not self.train_baseline_model():
                return False
            
            # Start all services
            if not self.start_all_services():
                print("❌ Failed to start system")
                self.shutdown_all()
                return False
            
            # Health check
            if not self.check_system_health():
                print("⚠️  Some services may not be fully healthy")
            
            # Start demo components
            self.start_demo_components()
            
            # Show info
            self.show_dashboard_info()
            
            # Keep running
            try:
                while True:
                    time.sleep(10)
                    # Periodic health check
                    if not self.check_system_health():
                        print("⚠️  Health check failed")
            except KeyboardInterrupt:
                pass
            
        except Exception as e:
            print(f"❌ System error: {e}")
        finally:
            self.shutdown_all()
        
        return True

if __name__ == "__main__":
    print("🚀 Enhanced Smart Transportation System")
    print("=====================================")
    
    manager = SystemManager()
    success = manager.run()
    
    sys.exit(0 if success else 1)