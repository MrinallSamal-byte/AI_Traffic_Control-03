#!/usr/bin/env python3
"""
Enhanced Prototype System Launcher
Orchestrates all services for the Smart Transportation System
"""

import subprocess
import time
import sys
import os
import json
import logging
import signal
import threading
from typing import Dict, List, Optional
import requests
import psutil
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages lifecycle of all system services"""
    
    def __init__(self):
        self.services = {}
        self.service_configs = self._load_service_configs()
        self.shutdown_event = threading.Event()
        self.health_check_thread = None
        
    def _load_service_configs(self) -> Dict[str, Dict]:
        """Load service configurations"""
        return {
            'redis': {
                'command': ['redis-server', '--port', '6379'],
                'health_url': None,
                'health_check': self._check_redis_health,
                'startup_delay': 2,
                'required': True,
                'description': 'Redis cache and message broker'
            },
            'postgres': {
                'command': ['pg_ctl', 'start', '-D', 'data'],
                'health_url': None,
                'health_check': self._check_postgres_health,
                'startup_delay': 3,
                'required': True,
                'description': 'PostgreSQL database'
            },
            'mosquitto': {
                'command': ['mosquitto', '-c', 'config/mosquitto.conf'],
                'health_url': None,
                'health_check': self._check_mosquitto_health,
                'startup_delay': 2,
                'required': True,
                'description': 'MQTT broker'
            },
            'blockchain': {
                'command': [sys.executable, 'blockchain/enhanced_blockchain_service.py'],
                'health_url': 'http://localhost:5003/health',
                'startup_delay': 5,
                'required': True,
                'description': 'Enhanced blockchain service'
            },
            'stream_processor': {
                'command': [sys.executable, 'stream_processor/processor.py'],
                'health_url': 'http://localhost:5004/health',
                'startup_delay': 3,
                'required': True,
                'description': 'Stream processor with validation'
            },
            'ml_services': {
                'command': [sys.executable, 'ml_services/enhanced_ml_api.py'],
                'health_url': 'http://localhost:5002/health',
                'startup_delay': 4,
                'required': True,
                'description': 'Enhanced ML services API'
            },
            'api_server': {
                'command': [sys.executable, 'api_server/app.py'],
                'health_url': 'http://localhost:5000/health',
                'startup_delay': 3,
                'required': True,
                'description': 'Main API server with WebSocket'
            },
            'websocket_manager': {
                'command': [sys.executable, 'api_server/websocket_manager.py'],
                'health_url': 'http://localhost:5001/health',
                'startup_delay': 2,
                'required': False,
                'description': 'WebSocket manager for real-time updates'
            },
            'device_simulator': {
                'command': [sys.executable, 'device_simulator/simulator.py'],
                'health_url': None,
                'startup_delay': 2,
                'required': False,
                'description': 'Device telemetry simulator'
            }
        }
    
    def start_service(self, service_name: str) -> bool:
        """Start a specific service"""
        if service_name in self.services:
            logger.warning(f"Service {service_name} is already running")
            return True
        
        config = self.service_configs.get(service_name)
        if not config:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        try:
            logger.info(f"Starting {service_name}: {config['description']}")
            
            # Start the process
            process = subprocess.Popen(
                config['command'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd(),
                env=os.environ.copy()
            )
            
            self.services[service_name] = {
                'process': process,
                'config': config,
                'started_at': datetime.now(),
                'healthy': False
            }
            
            # Wait for startup
            time.sleep(config['startup_delay'])
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"Service {service_name} failed to start:")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                del self.services[service_name]
                return False
            
            logger.info(f"✓ {service_name} started successfully (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop a specific service"""
        if service_name not in self.services:
            logger.warning(f"Service {service_name} is not running")
            return True
        
        try:
            service_info = self.services[service_name]
            process = service_info['process']
            
            logger.info(f"Stopping {service_name}...")
            
            # Try graceful shutdown first
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {service_name}")
                process.kill()
                process.wait()
            
            del self.services[service_name]
            logger.info(f"✓ {service_name} stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop {service_name}: {e}")
            return False
    
    def check_service_health(self, service_name: str) -> bool:
        """Check health of a specific service"""
        if service_name not in self.services:
            return False
        
        service_info = self.services[service_name]
        config = service_info['config']
        
        # Check if process is still running
        if service_info['process'].poll() is not None:
            logger.error(f"Service {service_name} process has died")
            return False
        
        # Use custom health check if available
        if config.get('health_check'):
            try:
                return config['health_check']()
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                return False
        
        # Use HTTP health check if URL is provided
        if config.get('health_url'):
            try:
                response = requests.get(config['health_url'], timeout=5)
                return response.status_code == 200
            except Exception as e:
                logger.debug(f"HTTP health check failed for {service_name}: {e}")
                return False
        
        # Default: assume healthy if process is running
        return True
    
    def _check_redis_health(self) -> bool:
        """Check Redis health"""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_timeout=2)
            r.ping()
            return True
        except Exception:
            return False
    
    def _check_postgres_health(self) -> bool:
        """Check PostgreSQL health"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='transport_system',
                user='admin',
                password='password',
                connect_timeout=2
            )
            conn.close()
            return True
        except Exception:
            return False
    
    def _check_mosquitto_health(self) -> bool:
        """Check Mosquitto MQTT broker health"""
        try:
            import paho.mqtt.client as mqtt
            client = mqtt.Client()
            client.connect('localhost', 1883, 2)
            client.disconnect()
            return True
        except Exception:
            return False
    
    def start_all_services(self) -> bool:
        """Start all services in dependency order"""
        logger.info("🚀 Starting Smart Transportation System...")
        
        # Define startup order (dependencies first)
        startup_order = [
            'redis',
            'postgres', 
            'mosquitto',
            'blockchain',
            'stream_processor',
            'ml_services',
            'api_server',
            'websocket_manager',
            'device_simulator'
        ]
        
        failed_services = []
        
        for service_name in startup_order:
            config = self.service_configs[service_name]
            
            if not self.start_service(service_name):
                if config['required']:
                    logger.error(f"Required service {service_name} failed to start")
                    failed_services.append(service_name)
                else:
                    logger.warning(f"Optional service {service_name} failed to start")
        
        if failed_services:
            logger.error(f"Failed to start required services: {failed_services}")
            return False
        
        # Start health monitoring
        self._start_health_monitoring()
        
        logger.info("✅ All services started successfully!")
        self._print_service_status()
        self._print_access_urls()
        
        return True
    
    def stop_all_services(self):
        """Stop all services"""
        logger.info("🛑 Stopping all services...")
        
        # Stop health monitoring
        if self.health_check_thread:
            self.shutdown_event.set()
            self.health_check_thread.join(timeout=5)
        
        # Stop services in reverse order
        service_names = list(self.services.keys())
        service_names.reverse()
        
        for service_name in service_names:
            self.stop_service(service_name)
        
        logger.info("✅ All services stopped")
    
    def _start_health_monitoring(self):
        """Start background health monitoring"""
        self.health_check_thread = threading.Thread(
            target=self._health_monitoring_loop,
            daemon=True
        )
        self.health_check_thread.start()
        logger.info("✓ Health monitoring started")
    
    def _health_monitoring_loop(self):
        """Background health monitoring loop"""
        while not self.shutdown_event.wait(30):  # Check every 30 seconds
            unhealthy_services = []
            
            for service_name in self.services:
                is_healthy = self.check_service_health(service_name)
                self.services[service_name]['healthy'] = is_healthy
                
                if not is_healthy:
                    unhealthy_services.append(service_name)
            
            if unhealthy_services:
                logger.warning(f"Unhealthy services detected: {unhealthy_services}")
    
    def _print_service_status(self):
        """Print current service status"""
        logger.info("\n📊 Service Status:")
        logger.info("-" * 60)
        
        for service_name, service_info in self.services.items():
            config = service_info['config']
            status = "🟢 RUNNING" if service_info.get('healthy', True) else "🔴 UNHEALTHY"
            pid = service_info['process'].pid
            
            logger.info(f"{service_name:20} {status:12} PID:{pid:6} - {config['description']}")
        
        logger.info("-" * 60)
    
    def _print_access_urls(self):
        """Print access URLs for services"""
        logger.info("\n🌐 Service Access URLs:")
        logger.info("-" * 60)
        
        urls = {
            'Main API': 'http://localhost:5000',
            'API Health': 'http://localhost:5000/health',
            'API Metrics': 'http://localhost:5000/metrics',
            'ML Services': 'http://localhost:5002',
            'ML Health': 'http://localhost:5002/health',
            'ML Docs': 'http://localhost:5002/docs',
            'Blockchain API': 'http://localhost:5003',
            'Blockchain Health': 'http://localhost:5003/health',
            'Stream Processor': 'http://localhost:5004/health',
            'WebSocket Manager': 'http://localhost:5001',
            'Real-time Dashboard': 'file:///' + os.path.abspath('dashboard/realtime_enhanced_dashboard.html')
        }
        
        for name, url in urls.items():
            logger.info(f"{name:20} {url}")
        
        logger.info("-" * 60)
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        stats = {
            'services': {},
            'system': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'uptime': time.time() - psutil.boot_time()
            }
        }
        
        for service_name, service_info in self.services.items():
            try:
                process = psutil.Process(service_info['process'].pid)
                stats['services'][service_name] = {
                    'healthy': service_info.get('healthy', False),
                    'cpu_percent': process.cpu_percent(),
                    'memory_mb': process.memory_info().rss / 1024 / 1024,
                    'uptime': time.time() - process.create_time()
                }
            except psutil.NoSuchProcess:
                stats['services'][service_name] = {
                    'healthy': False,
                    'status': 'dead'
                }
        
        return stats

def setup_signal_handlers(service_manager: ServiceManager):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"\nReceived signal {signum}, shutting down...")
        service_manager.stop_all_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def run_demo_scenario(service_manager: ServiceManager):
    """Run a demo scenario to showcase the system"""
    logger.info("\n🎬 Running demo scenario...")
    
    try:
        # Wait for services to be fully ready
        time.sleep(10)
        
        # Generate some demo telemetry data
        logger.info("📡 Generating demo telemetry data...")
        demo_script = os.path.join('tools', 'demo_data_generator.py')
        if os.path.exists(demo_script):
            subprocess.run([sys.executable, demo_script, '--count', '50'], timeout=30)
        
        # Trigger some ML predictions
        logger.info("🤖 Triggering ML predictions...")
        ml_demo_data = {
            "deviceId": "DEMO_DEVICE_001",
            "speed": 85.0,
            "accel_x": 8.5,
            "accel_y": 3.2,
            "accel_z": 9.8,
            "jerk": 6.0,
            "yaw_rate": 15.0
        }
        
        try:
            response = requests.post(
                'http://localhost:5002/predict',
                json=ml_demo_data,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"🎯 ML Prediction: {result['prediction']:.1f}% risk, {result['risk_level']} level")
        except Exception as e:
            logger.warning(f"ML prediction demo failed: {e}")
        
        # Simulate a toll event
        logger.info("💰 Simulating toll event...")
        toll_data = {
            "device_id": "DEMO_DEVICE_001",
            "gantry_id": "GANTRY_001",
            "location": {"lat": 20.2961, "lon": 85.8245},
            "timestamp": datetime.now().isoformat() + 'Z'
        }
        
        try:
            response = requests.post(
                'http://localhost:5000/toll/charge',
                json=toll_data,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"💳 Toll charged: {result.get('amount', 0)} ETH")
        except Exception as e:
            logger.warning(f"Toll demo failed: {e}")
        
        logger.info("✅ Demo scenario completed!")
        
    except Exception as e:
        logger.error(f"Demo scenario failed: {e}")

def main():
    """Main function"""
    logger.info("🚗 Smart Transportation System - Enhanced Prototype")
    logger.info("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)
    
    # Check if running in correct directory
    if not os.path.exists('api_server'):
        logger.error("Please run this script from the project root directory")
        sys.exit(1)
    
    # Initialize service manager
    service_manager = ServiceManager()
    
    # Setup signal handlers
    setup_signal_handlers(service_manager)
    
    try:
        # Start all services
        if not service_manager.start_all_services():
            logger.error("Failed to start system")
            sys.exit(1)
        
        # Run demo scenario
        if '--demo' in sys.argv:
            run_demo_scenario(service_manager)
        
        # Keep running and monitor
        logger.info("\n🔄 System is running. Press Ctrl+C to stop.")
        logger.info("💡 Open the dashboard: dashboard/realtime_enhanced_dashboard.html")
        
        # Print stats periodically
        while True:
            time.sleep(60)  # Print stats every minute
            stats = service_manager.get_system_stats()
            logger.info(f"📈 System: CPU {stats['system']['cpu_percent']:.1f}%, "
                       f"Memory {stats['system']['memory_percent']:.1f}%, "
                       f"Services: {len([s for s in stats['services'].values() if s.get('healthy')])}/{len(stats['services'])} healthy")
    
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        service_manager.stop_all_services()

if __name__ == "__main__":
    main()