#!/usr/bin/env python3
"""
Updated System Startup Script with React Frontend
"""

import subprocess
import time
import sys
import os
import signal
import threading
from pathlib import Path

class SystemManager:
    def __init__(self):
        self.processes = {}
        self.running = False
        
    def start_service(self, name, command, cwd=None, delay=0):
        if delay > 0:
            print(f"⏳ Waiting {delay}s before starting {name}...")
            time.sleep(delay)
        
        try:
            print(f"🚀 Starting {name}...")
            
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes[name] = process
            print(f"✓ {name} started (PID: {process.pid})")
            
        except Exception as e:
            print(f"✗ Failed to start {name}: {e}")
    
    def start_infrastructure(self):
        print("🏗️  Starting infrastructure services...")
        
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except:
            print("✗ Docker not found. Please install Docker and try again.")
            return False
        
        self.start_service("Infrastructure", "docker-compose up -d", cwd=".")
        print("⏳ Waiting for infrastructure services to be ready...")
        time.sleep(30)
        return True
    
    def start_backend_services(self):
        print("🔧 Starting backend services...")
        
        services = [
            {"name": "Stream Processor", "command": "python stream_processor/processor.py", "delay": 5},
            {"name": "ML Service", "command": "python ml_services/driver_scoring.py", "delay": 10},
            {"name": "API Server", "command": "python api_server/app.py", "delay": 15},
            {"name": "Blockchain Service", "command": "python blockchain/blockchain_service.py", "delay": 20},
            {"name": "WebSocket Server", "command": "python api_server/websocket_server.py", "delay": 25}
        ]
        
        for service in services:
            thread = threading.Thread(
                target=self.start_service,
                args=(service["name"], service["command"]),
                kwargs={"delay": service["delay"]}
            )
            thread.daemon = True
            thread.start()
    
    def start_frontend(self):
        print("🌐 Starting React frontend...")
        
        # Check if node_modules exists, if not install dependencies
        frontend_path = Path("frontend")
        if not (frontend_path / "node_modules").exists():
            print("📦 Installing frontend dependencies...")
            self.start_service(
                "NPM Install",
                "npm install",
                cwd="frontend",
                delay=30
            )
            time.sleep(60)  # Wait for npm install to complete
        
        # Start React development server
        self.start_service(
            "React Frontend",
            "npm start",
            cwd="frontend",
            delay=35
        )
    
    def start_simulators(self):
        print("🚗 Starting vehicle simulators...")
        time.sleep(40)
        
        self.start_service(
            "Vehicle Simulators",
            "python device_simulator/simulator.py --count 3",
            delay=5
        )
    
    def check_service_health(self):
        import requests
        
        services = [
            ("API Server", "http://localhost:5000/health"),
            ("ML Service", "http://localhost:5001/health"),
            ("Blockchain Service", "http://localhost:5002/health"),
            ("WebSocket Server", "http://localhost:5003/ws/health"),
            ("React Frontend", "http://localhost:3000")
        ]
        
        print("\n🔍 Checking service health...")
        
        for name, url in services:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✓ {name}: Healthy")
                else:
                    print(f"⚠️  {name}: Unhealthy (Status: {response.status_code})")
            except Exception as e:
                print(f"✗ {name}: Unreachable ({e})")
    
    def show_access_info(self):
        print("\n" + "="*60)
        print("🎛️  SMART TRANSPORTATION SYSTEM")
        print("="*60)
        print("🌐 React Frontend: http://localhost:3000")
        print("📊 API Server: http://localhost:5000/api/v1")
        print("🧠 ML Service: http://localhost:5001")
        print("⛓️  Blockchain: http://localhost:5002")
        print("🔌 WebSocket: http://localhost:5003")
        print("\n📡 MQTT Broker: localhost:1883")
        print("🗄️  Database: localhost:5432")
        print("\n🔐 Demo Credentials:")
        print("   User: user@example.com / password123")
        print("   Admin: admin@example.com / admin123")
        print("="*60)
    
    def stop_all_services(self):
        print("\n🛑 Stopping all services...")
        
        for name, process in self.processes.items():
            try:
                print(f"Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"Error stopping {name}: {e}")
        
        try:
            subprocess.run(["docker-compose", "down"], cwd=".", timeout=30)
            print("✓ Infrastructure services stopped")
        except Exception as e:
            print(f"Error stopping infrastructure: {e}")
        
        self.processes.clear()
        self.running = False
    
    def run(self):
        print("🚀 Starting Smart Transportation System with React Frontend...")
        print("Press Ctrl+C to stop all services\n")
        
        try:
            if not self.start_infrastructure():
                return
            
            self.start_backend_services()
            self.start_frontend()
            self.start_simulators()
            
            print("⏳ Waiting for all services to stabilize...")
            time.sleep(60)
            
            self.check_service_health()
            self.show_access_info()
            
            self.running = True
            
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested...")
        except Exception as e:
            print(f"\n✗ System error: {e}")
        finally:
            self.stop_all_services()
            print("✓ System shutdown complete")

def setup_signal_handlers(manager):
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}")
        manager.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def check_prerequisites():
    print("🔍 Checking prerequisites...")
    
    requirements = [
        ("Python", ["python", "--version"]),
        ("Node.js", ["node", "--version"]),
        ("NPM", ["npm", "--version"]),
        ("Docker", ["docker", "--version"]),
        ("Docker Compose", ["docker-compose", "--version"])
    ]
    
    missing = []
    
    for name, command in requirements:
        try:
            subprocess.run(command, check=True, capture_output=True)
            print(f"✓ {name} found")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"✗ {name} not found")
            missing.append(name)
    
    if missing:
        print(f"\n❌ Missing prerequisites: {', '.join(missing)}")
        print("Please install the missing components and try again.")
        return False
    
    print("✓ All prerequisites found\n")
    return True

def install_dependencies():
    print("📦 Installing dependencies...")
    
    # Install Python dependencies
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print("✓ Python dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install Python dependencies: {e}")
        return False
    
    return True

def main():
    print("🚗 Smart Transportation System with React Frontend")
    print("=" * 60)
    
    if not check_prerequisites():
        sys.exit(1)
    
    if not install_dependencies():
        sys.exit(1)
    
    manager = SystemManager()
    setup_signal_handlers(manager)
    
    manager.run()

if __name__ == "__main__":
    main()