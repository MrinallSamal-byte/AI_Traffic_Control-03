#!/usr/bin/env python3
"""
Prototype Startup Script
Orchestrates the complete system startup for demo purposes
"""

import subprocess
import time
import sys
import os
import requests
import json
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PrototypeManager:
    def __init__(self):
        self.services = {
            'infrastructure': [
                {'name': 'Docker Infrastructure', 'command': ['docker-compose', 'up', '-d'], 'cwd': '.'},
            ],
            'applications': [
                {'name': 'Stream Processor', 'command': ['python', 'processor.py'], 'cwd': 'stream_processor', 'port': 5004},
                {'name': 'ML Services', 'command': ['python', 'serve.py'], 'cwd': 'ml_services', 'port': 5002},
                {'name': 'Blockchain Service', 'command': ['python', 'blockchain_service.py'], 'cwd': 'blockchain', 'port': 5003},
                {'name': 'API Server', 'command': ['python', 'app.py'], 'cwd': 'api_server', 'port': 5000},
            ]
        }
        self.processes = {}
    
    def check_prerequisites(self):
        """Check if all prerequisites are installed"""
        logger.info("Checking prerequisites...")
        
        # Check Docker
        try:
            subprocess.run(['docker', '--version'], check=True, capture_output=True)
            subprocess.run(['docker-compose', '--version'], check=True, capture_output=True)
            logger.info("✓ Docker and Docker Compose found")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("✗ Docker or Docker Compose not found")
            return False
        
        # Check Python dependencies
        try:
            import paho.mqtt.client
            import kafka
            import flask
            import fastapi
            import web3
            logger.info("✓ Python dependencies found")
        except ImportError as e:
            logger.error(f"✗ Missing Python dependency: {e}")
            logger.info("Run: pip install -r requirements.txt")
            return False
        
        return True
    
    def start_infrastructure(self):
        """Start Docker infrastructure services"""
        logger.info("Starting infrastructure services...")
        
        try:
            subprocess.run(['docker-compose', 'up', '-d'], check=True, cwd='.')
            logger.info("✓ Infrastructure services started")
            
            # Wait for services to be ready
            logger.info("Waiting for infrastructure services to be ready...")
            time.sleep(30)
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Failed to start infrastructure: {e}")
            return False
    
    def check_infrastructure_health(self):
        """Check if infrastructure services are healthy"""
        logger.info("Checking infrastructure health...")
        
        checks = [
            {'name': 'PostgreSQL', 'command': ['docker', 'exec', '-it', 'protopype_timescaledb_1', 'pg_isready', '-U', 'admin']},
            {'name': 'Redis', 'command': ['docker', 'exec', '-it', 'protopype_redis_1', 'redis-cli', 'ping']},
            {'name': 'Kafka', 'url': 'http://localhost:9092'},
            {'name': 'Ganache', 'url': 'http://localhost:8545'},
        ]
        
        all_healthy = True
        for check in checks:
            if 'command' in check:
                try:
                    result = subprocess.run(check['command'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info(f"✓ {check['name']} is healthy")
                    else:
                        logger.warning(f"⚠ {check['name']} health check failed")
                        all_healthy = False
                except Exception as e:
                    logger.warning(f"⚠ {check['name']} health check error: {e}")
                    all_healthy = False
            elif 'url' in check:
                try:
                    response = requests.get(check['url'], timeout=5)
                    logger.info(f"✓ {check['name']} is healthy")
                except Exception:
                    logger.warning(f"⚠ {check['name']} is not responding")
                    all_healthy = False
        
        return all_healthy
    
    def train_ml_model(self):
        """Train ML model if not exists"""
        model_path = os.path.join('ml', 'models', 'harsh_driving_model_latest.pkl')
        
        if os.path.exists(model_path):
            logger.info("✓ ML model already exists")
            return True
        
        logger.info("Training ML model...")
        try:
            subprocess.run([
                'python', 'train_enhanced.py', '--samples', '10000'
            ], check=True, cwd='ml/training')
            logger.info("✓ ML model trained successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Failed to train ML model: {e}")
            return False
    
    def start_application_service(self, service):
        """Start a single application service"""
        logger.info(f"Starting {service['name']}...")
        
        try:
            process = subprocess.Popen(
                service['command'],
                cwd=service['cwd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[service['name']] = process
            
            # Wait a bit for service to start
            time.sleep(5)
            
            # Check if service is still running
            if process.poll() is None:
                logger.info(f"✓ {service['name']} started (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"✗ {service['name']} failed to start")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Failed to start {service['name']}: {e}")
            return False
    
    def start_application_services(self):
        """Start all application services"""
        logger.info("Starting application services...")
        
        # Start services sequentially with delays
        for service in self.services['applications']:
            if not self.start_application_service(service):
                return False
            time.sleep(3)  # Stagger startup
        
        return True
    
    def check_application_health(self):
        """Check health of application services"""
        logger.info("Checking application service health...")
        
        health_endpoints = [
            {'name': 'API Server', 'url': 'http://localhost:5000/health'},
            {'name': 'ML Services', 'url': 'http://localhost:5002/health'},
            {'name': 'Stream Processor', 'url': 'http://localhost:5004/health'},
            {'name': 'Blockchain Service', 'url': 'http://localhost:5003/health'},
        ]
        
        all_healthy = True
        for endpoint in health_endpoints:
            try:
                response = requests.get(endpoint['url'], timeout=10)
                if response.status_code == 200:
                    logger.info(f"✓ {endpoint['name']} is healthy")
                else:
                    logger.warning(f"⚠ {endpoint['name']} returned status {response.status_code}")
                    all_healthy = False
            except Exception as e:
                logger.warning(f"⚠ {endpoint['name']} health check failed: {e}")
                all_healthy = False
        
        return all_healthy
    
    def run_demo(self):
        """Run demo data generator"""
        logger.info("Starting demo data generation...")
        
        try:
            subprocess.run([
                'python', 'demo_data_generator.py', 
                '--vehicles', '5', 
                '--duration', '10'
            ], check=True, cwd='tools')
            logger.info("✓ Demo completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Demo failed: {e}")
            return False
    
    def show_access_info(self):
        """Show access information for the user"""
        logger.info("\n" + "="*60)
        logger.info("🚀 PROTOTYPE READY!")
        logger.info("="*60)
        logger.info("Access Points:")
        logger.info("  • Dashboard: http://localhost:3000/realtime_enhanced.html")
        logger.info("  • API Server: http://localhost:5000")
        logger.info("  • ML Services: http://localhost:5002")
        logger.info("  • Grafana: http://localhost:3001 (admin/admin)")
        logger.info("  • Prometheus: http://localhost:9090")
        logger.info("")
        logger.info("Credentials:")
        logger.info("  • Admin: admin/admin123")
        logger.info("  • Operator: operator/operator123")
        logger.info("")
        logger.info("Demo Commands:")
        logger.info("  • Health Check: make health")
        logger.info("  • View Metrics: make metrics")
        logger.info("  • Run Demo: make demo")
        logger.info("="*60)
    
    def cleanup(self):
        """Clean up processes"""
        logger.info("Cleaning up...")
        
        for name, process in self.processes.items():
            if process.poll() is None:
                logger.info(f"Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
    
    def start_prototype(self):
        """Start the complete prototype"""
        try:
            # Check prerequisites
            if not self.check_prerequisites():
                return False
            
            # Start infrastructure
            if not self.start_infrastructure():
                return False
            
            # Check infrastructure health
            if not self.check_infrastructure_health():
                logger.warning("Some infrastructure services may not be fully ready")
            
            # Train ML model
            if not self.train_ml_model():
                return False
            
            # Start application services
            if not self.start_application_services():
                return False
            
            # Wait for services to stabilize
            logger.info("Waiting for services to stabilize...")
            time.sleep(10)
            
            # Check application health
            if not self.check_application_health():
                logger.warning("Some application services may not be fully ready")
            
            # Show access information
            self.show_access_info()
            
            return True
            
        except KeyboardInterrupt:
            logger.info("Startup interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during startup: {e}")
            return False

def main():
    manager = PrototypeManager()
    
    try:
        success = manager.start_prototype()
        
        if success:
            logger.info("Prototype started successfully!")
            logger.info("Press Ctrl+C to stop all services")
            
            # Keep running until interrupted
            while True:
                time.sleep(1)
        else:
            logger.error("Failed to start prototype")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down prototype...")
    finally:
        manager.cleanup()

if __name__ == "__main__":
    main()