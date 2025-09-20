#!/usr/bin/env python3
"""
Full System Startup Script for Smart Transportation System
Starts all components in the correct order with health checks
"""

import subprocess
import time
import requests
import os
import sys
import signal
import threading
from pathlib import Path

class SystemManager:
    def __init__(self):
        self.processes = {}
        self.base_dir = Path(__file__).parent
        self.running = True
        
        # Service configurations
        self.services = {
            'stream_processor': {
                'cmd': [sys.executable, 'processor.py'],
                'cwd': self.base_dir / 'stream_processor',
                'health_url': 'http://localhost:5004/health',
                'startup_delay': 2
            },
            'api_server': {
                'cmd': [sys.executable, 'app.py'],
                'cwd': self.base_dir / 'api_server',
                'health_url': 'http://localhost:5000/health',
                'startup_delay': 3
            },
            'ml_services': {
                'cmd': [sys.executable, 'serve.py'],
                'cwd': self.base_dir / 'ml_services',
                'health_url': 'http://localhost:5002/health',
                'startup_delay': 4
            },
            'blockchain_service': {
                'cmd': [sys.executable, 'blockchain_service.py'],
                'cwd': self.base_dir / 'blockchain',
                'health_url': 'http://localhost:5002/health',
                'startup_delay': 5
            }
        }
    
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        print("🔍 Checking prerequisites...")
        
        # Check Python packages
        required_packages = [
            'flask', 'fastapi', 'pydantic', 'sklearn', 'joblib',
            'prometheus_client', 'paho-mqtt', 'psycopg2', 'redis'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"✗ Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False
        
        # Check if ML model exists
        model_path = self.base_dir / 'ml' / 'models' / 'harsh_driving_model_latest.pkl'
        if not model_path.exists():
            print("✗ ML model not found. Training model...")
            self.train_ml_model()
        
        print("✓ Prerequisites check passed")
        return True
    
    def train_ml_model(self):
        """Train the ML model if it doesn't exist"""
        try:
            training_script = self.base_dir / 'ml' / 'training' / 'train_harsh_driving.py'
            result = subprocess.run(
                [sys.executable, str(training_script)],
                cwd=self.base_dir / 'ml' / 'training',
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print("✓ ML model trained successfully")
            else:
                print(f"✗ ML model training failed: {result.stderr}")
                
        except Exception as e:
            print(f"✗ Failed to train ML model: {e}")
    
    def start_service(self, name, config):
        """Start a single service"""
        print(f"🚀 Starting {name}...")
        
        try:
            process = subprocess.Popen(
                config['cmd'],
                cwd=config['cwd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[name] = process
            
            # Wait for startup
            time.sleep(config['startup_delay'])
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"✗ {name} failed to start:")
                print(f"   stdout: {stdout}")
                print(f"   stderr: {stderr}")
                return False
            
            print(f"✓ {name} started (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"✗ Failed to start {name}: {e}")
            return False
    
    def check_health(self, name, config):
        """Check service health"""
        if 'health_url' not in config:
            return True
        
        try:
            response = requests.get(config['health_url'], timeout=5)
            if response.status_code == 200:
                print(f"✓ {name} health check passed")
                return True
            else:
                print(f"✗ {name} health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ {name} health check failed: {e}")
            return False
    
    def start_all_services(self):
        """Start all services in order"""
        print("🚀 Starting Smart Transportation System...")
        
        if not self.check_prerequisites():
            return False
        
        # Start services in order
        for name, config in self.services.items():
            if not self.start_service(name, config):
                print(f"✗ Failed to start {name}, aborting...")
                self.stop_all_services()
                return False
        
        # Wait a bit for all services to fully initialize
        print("⏳ Waiting for services to initialize...")
        time.sleep(10)
        
        # Health checks
        print("🏥 Running health checks...")
        all_healthy = True
        for name, config in self.services.items():
            if not self.check_health(name, config):
                all_healthy = False
        
        if all_healthy:
            print("✅ All services started successfully!")
            self.print_service_urls()
            return True
        else:
            print("⚠️  Some services may not be fully ready")
            self.print_service_urls()
            return True
    
    def print_service_urls(self):
        """Print service URLs for easy access"""
        print("\n📋 Service URLs:")
        print("   API Server:      http://localhost:5000")
        print("   ML Services:     http://localhost:5002")
        print("   Stream Processor: http://localhost:5004")
        print("   Blockchain:      http://localhost:5002")
        print("   Dashboard:       file://" + str(self.base_dir / 'dashboard' / 'realtime_dashboard.html'))
        print("\n📊 Monitoring:")
        print("   API Metrics:     http://localhost:5000/metrics")
        print("   ML Metrics:      http://localhost:5002/metrics")
        print("   Health Checks:   http://localhost:5000/health")
        print("\n🔐 Authentication:")
        print("   Username: admin")
        print("   Password: password")
    
    def stop_all_services(self):
        """Stop all running services"""
        print("\n🛑 Stopping all services...")
        
        for name, process in self.processes.items():
            if process and process.poll() is None:
                print(f"   Stopping {name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"   ✓ {name} stopped")
                except subprocess.TimeoutExpired:
                    print(f"   Force killing {name}...")
                    process.kill()
                    process.wait()
                    print(f"   ✓ {name} force stopped")
                except Exception as e:
                    print(f"   ✗ Error stopping {name}: {e}")
        
        self.processes.clear()
        print("✅ All services stopped")
    
    def monitor_services(self):
        """Monitor running services and restart if needed"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            
            for name, process in list(self.processes.items()):
                if process.poll() is not None:
                    print(f"⚠️  {name} has stopped unexpectedly")
                    # Could implement restart logic here
            
            if not self.running:
                break
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n📡 Received signal {signum}, shutting down...")
        self.running = False
        self.stop_all_services()
        sys.exit(0)
    
    def run(self):
        """Main run method"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            if self.start_all_services():
                print("\n🎯 System is running! Press Ctrl+C to stop.")
                
                # Start monitoring thread
                monitor_thread = threading.Thread(target=self.monitor_services, daemon=True)
                monitor_thread.start()
                
                # Keep main thread alive
                while self.running:
                    time.sleep(1)
            else:
                print("✗ Failed to start system")
                return 1
                
        except KeyboardInterrupt:
            print("\n⏹️  Shutdown requested by user")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
        finally:
            self.stop_all_services()
        
        return 0

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Transportation System Manager')
    parser.add_argument('--check-only', action='store_true', help='Only check prerequisites')
    parser.add_argument('--train-model', action='store_true', help='Train ML model and exit')
    parser.add_argument('--generate-data', action='store_true', help='Generate sample data')
    
    args = parser.parse_args()
    
    manager = SystemManager()
    
    if args.check_only:
        if manager.check_prerequisites():
            print("✅ System ready to start")
            return 0
        else:
            print("✗ Prerequisites not met")
            return 1
    
    if args.train_model:
        manager.train_ml_model()
        return 0
    
    if args.generate_data:
        print("🎲 Starting sample data generation...")
        try:
            from tools.generate_sample_telemetry import TelemetryGenerator
            generator = TelemetryGenerator()
            generator.run_simulation(num_devices=5, duration_seconds=60)
        except ImportError:
            print("✗ Sample data generator not available")
            return 1
        return 0
    
    # Start the full system
    return manager.run()

if __name__ == "__main__":
    sys.exit(main())