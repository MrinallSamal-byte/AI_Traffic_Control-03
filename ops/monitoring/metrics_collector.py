#!/usr/bin/env python3
"""
Metrics Collector - Prometheus metrics and structured logging
"""

import time
import json
import logging
import uuid
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from functools import wraps
import psutil
import threading

# Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections', ['type'])
TELEMETRY_MESSAGES = Counter('telemetry_messages_total', 'Total telemetry messages', ['device_id', 'status'])
ML_PREDICTIONS = Counter('ml_predictions_total', 'ML model predictions', ['model', 'status'])
SYSTEM_CPU = Gauge('system_cpu_percent', 'System CPU usage')
SYSTEM_MEMORY = Gauge('system_memory_percent', 'System memory usage')
KAFKA_LAG = Gauge('kafka_consumer_lag', 'Kafka consumer lag', ['topic', 'partition'])

class StructuredLogger:
    """Structured logging with correlation IDs"""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # JSON formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def info(self, message, correlation_id=None, **kwargs):
        self._log('info', message, correlation_id, **kwargs)
    
    def warning(self, message, correlation_id=None, **kwargs):
        self._log('warning', message, correlation_id, **kwargs)
    
    def error(self, message, correlation_id=None, **kwargs):
        self._log('error', message, correlation_id, **kwargs)
    
    def _log(self, level, message, correlation_id=None, **kwargs):
        log_data = {
            'message': message,
            'correlation_id': correlation_id or str(uuid.uuid4()),
            **kwargs
        }
        
        getattr(self.logger, level)(json.dumps(log_data))

# Global logger instance
structured_logger = StructuredLogger('transport_system')

def track_api_metrics(f):
    """Decorator to track API metrics"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        method = getattr(f, '__method__', 'GET')
        endpoint = getattr(f, '__endpoint__', f.__name__)
        
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        try:
            # Log request start
            structured_logger.info(
                f"API request started: {method} {endpoint}",
                correlation_id=correlation_id,
                method=method,
                endpoint=endpoint
            )
            
            result = f(*args, **kwargs)
            
            # Track success metrics
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status='success').inc()
            
            # Log request completion
            structured_logger.info(
                f"API request completed: {method} {endpoint}",
                correlation_id=correlation_id,
                method=method,
                endpoint=endpoint,
                duration=time.time() - start_time
            )
            
            return result
            
        except Exception as e:
            # Track error metrics
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status='error').inc()
            
            # Log error
            structured_logger.error(
                f"API request failed: {method} {endpoint}",
                correlation_id=correlation_id,
                method=method,
                endpoint=endpoint,
                error=str(e),
                duration=time.time() - start_time
            )
            
            raise
        
        finally:
            # Track duration
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(time.time() - start_time)
    
    return decorated_function

def track_telemetry_processing(device_id, status='success'):
    """Track telemetry message processing"""
    TELEMETRY_MESSAGES.labels(device_id=device_id, status=status).inc()
    
    structured_logger.info(
        "Telemetry message processed",
        device_id=device_id,
        status=status,
        timestamp=datetime.utcnow().isoformat()
    )

def track_ml_prediction(model_name, status='success'):
    """Track ML model predictions"""
    ML_PREDICTIONS.labels(model=model_name, status=status).inc()
    
    structured_logger.info(
        "ML prediction completed",
        model=model_name,
        status=status,
        timestamp=datetime.utcnow().isoformat()
    )

class SystemMetricsCollector:
    """Collect system metrics"""
    
    def __init__(self, interval=30):
        self.interval = interval
        self.running = False
    
    def start(self):
        """Start metrics collection"""
        self.running = True
        thread = threading.Thread(target=self._collect_loop)
        thread.daemon = True
        thread.start()
        structured_logger.info("System metrics collection started")
    
    def stop(self):
        """Stop metrics collection"""
        self.running = False
        structured_logger.info("System metrics collection stopped")
    
    def _collect_loop(self):
        """Main collection loop"""
        while self.running:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                SYSTEM_CPU.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                SYSTEM_MEMORY.set(memory.percent)
                
                # Log system metrics
                structured_logger.info(
                    "System metrics collected",
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_available=memory.available,
                    timestamp=datetime.utcnow().isoformat()
                )
                
                time.sleep(self.interval)
                
            except Exception as e:
                structured_logger.error(
                    "Error collecting system metrics",
                    error=str(e)
                )
                time.sleep(self.interval)

class AlertManager:
    """Manage alerts based on metrics"""
    
    def __init__(self):
        self.alert_rules = {
            'high_cpu': {'threshold': 80, 'duration': 300},  # 80% for 5 minutes
            'high_memory': {'threshold': 85, 'duration': 300},
            'high_api_latency': {'threshold': 2.0, 'duration': 60},  # 2 seconds
            'high_error_rate': {'threshold': 0.05, 'duration': 300}  # 5% error rate
        }
        self.alert_states = {}
    
    def check_alerts(self):
        """Check alert conditions"""
        try:
            # Check CPU alert
            cpu_percent = psutil.cpu_percent()
            self._check_threshold_alert('high_cpu', cpu_percent)
            
            # Check memory alert
            memory_percent = psutil.virtual_memory().percent
            self._check_threshold_alert('high_memory', memory_percent)
            
            # Additional checks would go here for API latency and error rates
            
        except Exception as e:
            structured_logger.error(
                "Error checking alerts",
                error=str(e)
            )
    
    def _check_threshold_alert(self, alert_name, current_value):
        """Check if threshold alert should fire"""
        rule = self.alert_rules[alert_name]
        threshold = rule['threshold']
        
        if current_value > threshold:
            if alert_name not in self.alert_states:
                self.alert_states[alert_name] = {
                    'start_time': time.time(),
                    'fired': False
                }
            
            # Check if alert should fire
            alert_state = self.alert_states[alert_name]
            if not alert_state['fired'] and (time.time() - alert_state['start_time']) > rule['duration']:
                self._fire_alert(alert_name, current_value, threshold)
                alert_state['fired'] = True
        else:
            # Clear alert state if value is below threshold
            if alert_name in self.alert_states:
                if self.alert_states[alert_name]['fired']:
                    self._clear_alert(alert_name, current_value)
                del self.alert_states[alert_name]
    
    def _fire_alert(self, alert_name, current_value, threshold):
        """Fire an alert"""
        structured_logger.warning(
            f"ALERT: {alert_name}",
            alert_name=alert_name,
            current_value=current_value,
            threshold=threshold,
            severity='warning',
            timestamp=datetime.utcnow().isoformat()
        )
    
    def _clear_alert(self, alert_name, current_value):
        """Clear an alert"""
        structured_logger.info(
            f"ALERT CLEARED: {alert_name}",
            alert_name=alert_name,
            current_value=current_value,
            timestamp=datetime.utcnow().isoformat()
        )

def start_monitoring(port=8000):
    """Start monitoring services"""
    # Start Prometheus metrics server
    start_http_server(port)
    structured_logger.info(f"Prometheus metrics server started on port {port}")
    
    # Start system metrics collection
    metrics_collector = SystemMetricsCollector()
    metrics_collector.start()
    
    # Start alert manager
    alert_manager = AlertManager()
    
    def alert_check_loop():
        while True:
            alert_manager.check_alerts()
            time.sleep(60)  # Check every minute
    
    alert_thread = threading.Thread(target=alert_check_loop)
    alert_thread.daemon = True
    alert_thread.start()
    
    structured_logger.info("Monitoring services started")
    
    return metrics_collector, alert_manager

if __name__ == "__main__":
    # Start monitoring
    collector, alerts = start_monitoring()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        collector.stop()
        structured_logger.info("Monitoring stopped")