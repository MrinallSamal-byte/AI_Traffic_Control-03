#!/usr/bin/env python3
"""
Smart Transportation System - System Startup Script
Orchestrates all services and provides unified control
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
        """Start a service with optional delay"""
        if delay > 0:
            print(f"⏳ Waiting {delay}s before starting {name}...")
            time.sleep(delay)
        
        try:
            print(f"🚀 Starting {name}...")
            
            if cwd:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            self.processes[name] = process
            print(f"✓ {name} started (PID: {process.pid})")
            
        except Exception as e:
            print(f"✗ Failed to start {name}: {e}")
    
    def start_infrastructure(self):
        """Start infrastructure services (Docker)"""
        print("🏗️  Starting infrastructure services...")
        
        # Check if Docker is running
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except:
            print("✗ Docker not found. Please install Docker and try again.")
            return False
        
        # Start Docker Compose services
        self.start_service(
            "Infrastructure",
            "docker-compose up -d",
            cwd="."
        )
        
        # Wait for services to be ready
        print("⏳ Waiting for infrastructure services to be ready...")
        time.sleep(30)
        
        return True
    
    def start_application_services(self):
        """Start application services"""
        print("🔧 Starting application services...")
        
        services = [
            {
                "name": "Stream Processor",
                "command": "python stream_processor/processor.py",
                "delay": 5
            },
            {
                "name": "ML Service",
                "command": "python ml_services/driver_scoring.py",
                "delay": 10
            },
            {
                "name": "API Server",
                "command": "python api_server/app.py",
                "delay": 15
            },
            {
                "name": "Blockchain Service",
                "command": "python blockchain/blockchain_service.py",
                "delay": 20
            }
        ]
        
        # Start services in separate threads with delays
        for service in services:
            thread = threading.Thread(
                target=self.start_service,
                args=(service["name"], service["command"]),
                kwargs={"delay": service["delay"]}
            )
            thread.daemon = True
            thread.start()
    
    def start_simulators(self):
        """Start device simulators"""
        print("🚗 Starting vehicle simulators...")
        
        # Wait a bit for services to be ready
        time.sleep(25)
        
        self.start_service(
            "Vehicle Simulators",
            "python device_simulator/simulator.py --count 3",
            delay=5
        )
    
    def check_service_health(self):
        """Check health of all services"""
        import requests
        
        services = [
            ("API Server", "http://localhost:5000/health"),
            ("ML Service", "http://localhost:5001/health"),
            ("Blockchain Service", "http://localhost:5002/health")
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
    
    def show_dashboard_info(self):
        """Show dashboard access information"""
        print("\n" + "="*60)
        print("🎛️  SMART TRANSPORTATION SYSTEM DASHBOARD")
        print("="*60)
        print("📊 Web Dashboard: http://localhost:3000")
        print("🔌 API Endpoints:")
        print("   • Main API: http://localhost:5000/api/v1")
        print("   • ML Service: http://localhost:5001")
        print("   • Blockchain: http://localhost:5002")
        print("\n📡 MQTT Broker: localhost:1883")
        print("🗄️  Database: localhost:5432 (transport_system)")
        print("🔗 Blockchain: http://localhost:8545")
        print("\n📋 Sample API Calls:")
        print("   • GET /api/v1/vehicles - List vehicles")
        print("   • GET /api/v1/admin/dashboard - Dashboard data")
        print("   • GET /api/v1/toll/gantries - Toll gantries")
        print("="*60)
    
    def start_dashboard_server(self):
        """Start simple HTTP server for dashboard"""
        print("🌐 Starting dashboard server...")
        
        self.start_service(
            "Dashboard Server",
            "python -m http.server 3000",
            cwd="dashboard",
            delay=30
        )
    
    def stop_all_services(self):
        """Stop all running services"""
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
        
        # Stop Docker services
        try:
            subprocess.run(["docker-compose", "down"], cwd=".", timeout=30)
            print("✓ Infrastructure services stopped")
        except Exception as e:
            print(f"Error stopping infrastructure: {e}")
        
        self.processes.clear()
        self.running = False
    
    def run(self):
        """Main run method"""
        print("🚀 Starting Smart Transportation System...")
        print("Press Ctrl+C to stop all services\n")
        
        try:
            # Start infrastructure
            if not self.start_infrastructure():
                return
            
            # Start application services
            self.start_application_services()
            
            # Start dashboard server
            self.start_dashboard_server()
            
            # Start simulators
            self.start_simulators()
            
            # Wait for services to stabilize
            print("⏳ Waiting for services to stabilize...")
            time.sleep(40)
            
            # Check health
            self.check_service_health()
            
            # Show dashboard info
            self.show_dashboard_info()
            
            self.running = True
            
            # Keep running until interrupted
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
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}")
        manager.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def check_prerequisites():
    """Check if all prerequisites are installed"""
    print("🔍 Checking prerequisites...")
    
    requirements = [
        ("Python", ["python", "--version"]),
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

def install_python_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print("✓ Python dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False
    
    return True

def main():
    """Main entry point"""
    print("🚗 Smart Transportation System Startup")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Install dependencies
    if not install_python_dependencies():
        sys.exit(1)
    
    # Create system manager
    manager = SystemManager()
    setup_signal_handlers(manager)
    
    # Run the system
    manager.run()

if __name__ == "__main__":
    main()