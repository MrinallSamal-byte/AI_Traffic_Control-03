#!/usr/bin/env python3
"""
API Server - MVP Prototype for Smart Transportation System
Simplified version with essential endpoints for ML model demo
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import sys
from datetime import datetime, timedelta
import logging
import time
import psutil
from collections import defaultdict
from functools import wraps
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Load environment variables
load_dotenv()

# Import enhanced authentication
from auth import (
    init_auth, user_manager, require_permission, require_role, 
    require_endpoint_access, rate_limit_by_user, create_token
)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Number of active connections')
TELEMETRY_MESSAGES = Counter('telemetry_messages_total', 'Total telemetry messages processed')
TOLL_TRANSACTIONS = Counter('toll_transactions_total', 'Total toll transactions', ['status'])
ML_PREDICTIONS = Counter('ml_predictions_total', 'Total ML predictions', ['model_type'])
ERROR_COUNT = Counter('errors_total', 'Total errors', ['error_type'])

# Add ml_services to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_services.driver_score import predict_score

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize enhanced authentication
jwt = init_auth(app)

# Metrics tracking
metrics = {
    'request_count': defaultdict(int),
    'error_count': defaultdict(int),
    'response_times': defaultdict(list)
}

# Rate limiting storage
rate_limit_storage = defaultdict(list)

def rate_limit(max_requests=100, window_seconds=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            now = time.time()
            
            # Clean old requests
            rate_limit_storage[client_ip] = [
                req_time for req_time in rate_limit_storage[client_ip]
                if now - req_time < window_seconds
            ]
            
            # Check rate limit
            if len(rate_limit_storage[client_ip]) >= max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Add current request
            rate_limit_storage[client_ip].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.before_request
def track_metrics():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    duration = time.time() - request.start_time
    endpoint = request.endpoint or 'unknown'
    
    # Track internal metrics
    metrics['request_count'][endpoint] += 1
    metrics['response_times'][endpoint].append(duration)
    
    if response.status_code >= 400:
        metrics['error_count'][endpoint] += 1
    
    # Prometheus metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(duration)
    
    # Structured logging
    logger.info(f"Request: {request.method} {request.path} - {response.status_code} - {duration:.3f}s")
    
    return response

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'api_server',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'uptime': time.time() - app.start_time,
        'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024,  # MB
        'cpu_percent': psutil.Process().cpu_percent()
    })

@app.route('/metrics', methods=['GET'])
def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/metrics/json', methods=['GET'])
def get_metrics():
    """Get basic metrics in JSON format"""
    return jsonify({
        'request_count': dict(metrics['request_count']),
        'error_count': dict(metrics['error_count']),
        'avg_response_time': {
            endpoint: sum(times) / len(times) if times else 0
            for endpoint, times in metrics['response_times'].items()
        },
        'active_connections': len(rate_limit_storage),
        'uptime_seconds': time.time() - app.start_time if hasattr(app, 'start_time') else 0
    })

# User management is now handled by auth module

# Authentication endpoints
@app.route('/auth/login', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=300)  # 5 attempts per 5 minutes
def login():
    """Secure login endpoint with enhanced authentication"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    # Authenticate user
    user_info = user_manager.authenticate_user(username, password)
    if user_info:
        access_token = create_token(username)
        
        logger.info(f"Successful login for user: {username} (role: {user_info['role']})")
        return jsonify({
            'access_token': access_token,
            'user': username,
            'role': user_info['role'],
            'permissions': user_info['permissions']
        })
    
    logger.warning(f"Failed login attempt for user: {username}")
    return jsonify({'error': 'Invalid credentials'}), 401

# Telemetry ingestion endpoint
@app.route('/telemetry/ingest', methods=['POST'])
@require_permission('write')
@rate_limit_by_user(max_requests=1000, window_seconds=60)
def ingest_telemetry():
    """Secure telemetry ingestion endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "invalid json"}), 400
        
        required_fields = ['deviceId', 'timestamp', 'location', 'speedKmph', 'acceleration', 'fuelLevel']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"missing field: {field}"}), 400
        
        # Validate location structure
        location = data.get('location', {})
        if 'lat' not in location or 'lon' not in location:
            return jsonify({"error": "invalid location format"}), 400
        
        # Validate acceleration structure
        acceleration = data.get('acceleration', {})
        if not all(key in acceleration for key in ['x', 'y', 'z']):
            return jsonify({"error": "invalid acceleration format"}), 400
        
        # Update metrics
        TELEMETRY_MESSAGES.inc()
        
        # Log telemetry ingestion
        logger.info(f"Telemetry ingested", extra={
            'device_id': data['deviceId'],
            'user': get_jwt_identity(),
            'timestamp': data['timestamp']
        })
        
        # In production, send to message queue for processing
        return jsonify({
            'status': 'accepted',
            'device_id': data['deviceId'],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"Telemetry ingestion error: {e}")
        return jsonify({"error": "internal error"}), 500

# Toll detection and charging
@app.route('/toll/charge', methods=['POST'])
@require_permission('write')
@rate_limit_by_user(max_requests=100, window_seconds=60)
def charge_toll():
    """Process toll charge when vehicle crosses gantry"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "invalid json"}), 400
        
        required_fields = ['device_id', 'gantry_id', 'location', 'timestamp']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"missing field: {field}"}), 400
        
        # Calculate toll amount based on vehicle type and distance
        toll_amount = calculate_toll_amount(data.get('vehicle_type', 'car'))
        
        # Mock vehicle address (in production, get from device registration)
        vehicle_address = f"0x{data['device_id'][:40].ljust(40, '0')}"
        
        # Call blockchain service
        import requests
        try:
            blockchain_response = requests.post('http://localhost:5002/toll/autopay', json={
                'vehicle_address': vehicle_address,
                'gantry_id': data['gantry_id'],
                'amount': toll_amount
            }, timeout=10)
            
            if blockchain_response.status_code == 200:
                blockchain_data = blockchain_response.json()
                
                # Prepare toll event data
                toll_event_data = {
                    'device_id': data['device_id'],
                    'gantry_id': data['gantry_id'],
                    'amount': toll_amount,
                    'toll_id': blockchain_data.get('toll_id'),
                    'tx_hash': blockchain_data.get('tx_hash'),
                    'paid': blockchain_data.get('paid', False),
                    'timestamp': data['timestamp'],
                    'location': data.get('location', {})
                }
                
                # Update metrics
                TOLL_TRANSACTIONS.labels(status='success').inc()
                
                # Broadcast toll event via WebSocket
                try:
                    from websocket_enhanced import websocket_manager
                    if websocket_manager:
                        websocket_manager.broadcast_toll_event(toll_event_data)
                except ImportError:
                    logger.warning("WebSocket manager not available for toll event broadcast")
                
                # Store toll event in database
                try:
                    store_toll_event(toll_event_data)
                except Exception as e:
                    logger.error(f"Failed to store toll event: {e}")
                
                # Log toll event
                logger.info(f"Toll charged successfully", extra=toll_event_data)
                
                return jsonify(toll_event_data)
            else:
                TOLL_TRANSACTIONS.labels(status='failed').inc()
                logger.error(f"Blockchain toll charge failed: {blockchain_response.text}")
                return jsonify({"error": "blockchain toll charge failed"}), 500
                
        except requests.RequestException as e:
            TOLL_TRANSACTIONS.labels(status='failed').inc()
            logger.error(f"Blockchain service connection failed: {e}")
            return jsonify({"error": "blockchain service unavailable"}), 503
            
    except Exception as e:
        logger.error(f"Toll charge error: {e}")
        return jsonify({"error": "internal error"}), 500

def calculate_toll_amount(vehicle_type):
    """Calculate toll amount based on vehicle type"""
    rates = {
        'car': 0.05,
        'truck': 0.15,
        'motorcycle': 0.03
    }
    return rates.get(vehicle_type, 0.05)

def store_toll_event(toll_data):
    """Store toll event in database"""
    try:
        import sqlite3
        conn = sqlite3.connect('prototype.db')
        cursor = conn.cursor()
        
        # Create toll_events table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS toll_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                gantry_id TEXT NOT NULL,
                amount REAL NOT NULL,
                toll_id INTEGER,
                tx_hash TEXT,
                paid BOOLEAN DEFAULT FALSE,
                timestamp TEXT NOT NULL,
                location_lat REAL,
                location_lon REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert toll event
        location = toll_data.get('location', {})
        cursor.execute('''
            INSERT INTO toll_events 
            (device_id, gantry_id, amount, toll_id, tx_hash, paid, timestamp, location_lat, location_lon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            toll_data['device_id'],
            toll_data['gantry_id'],
            toll_data['amount'],
            toll_data.get('toll_id'),
            toll_data.get('tx_hash'),
            toll_data.get('paid', False),
            toll_data['timestamp'],
            location.get('lat'),
            location.get('lon')
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Toll event stored in database: {toll_data['device_id']}")
        
    except Exception as e:
        logger.error(f"Failed to store toll event in database: {e}")

# Driver scoring endpoint
@app.route('/driver_score', methods=['POST'])
@require_permission('read')
@rate_limit_by_user(max_requests=200, window_seconds=60)
def driver_score():
    """Calculate driver score from telemetry data"""
    try:
        telemetry = request.get_json()
        if not telemetry:
            return jsonify({"error": "invalid json"}), 400
        
        # Validate required fields
        required_fields = ['device_id', 'timestamp']
        for field in required_fields:
            if field not in telemetry:
                return jsonify({"error": f"missing field: {field}"}), 400
        
        # Get driver score from ML service
        score_result = predict_score(telemetry)
        
        # Update metrics
        ML_PREDICTIONS.labels(model_type=score_result.get('model', 'unknown')).inc()
        
        # Structured logging with context
        logger.info(f"Driver score request", extra={
            'device_id': telemetry.get('device_id'),
            'score': score_result['score'],
            'user': get_jwt_identity(),
            'request_id': request.headers.get('X-Request-ID', 'unknown')
        })
        
        response = {
            "device_id": telemetry.get("device_id"),
            "timestamp": telemetry.get("timestamp"),
            "driver_score": score_result["score"],
            "model": score_result["model"]
        }
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Driver score error: {e}", extra={
            'device_id': telemetry.get('device_id', 'unknown'),
            'user': get_jwt_identity(),
            'request_id': request.headers.get('X-Request-ID', 'unknown')
        })
        return jsonify({"error": "internal error"}), 500

# WebSocket endpoint for real-time streaming
@app.route('/ws/telemetry')
def websocket_telemetry():
    """WebSocket endpoint for real-time telemetry streaming"""
    from flask_socketio import SocketIO, emit, join_room, leave_room
    
    # This would be implemented with Flask-SocketIO in production
    return jsonify({
        'message': 'WebSocket endpoint - use Flask-SocketIO for full implementation',
        'endpoint': '/ws/telemetry',
        'events': ['telemetry_update', 'vehicle_status', 'toll_event']
    })

@app.route('/stream/telemetry', methods=['GET'])
@require_permission('read')
def stream_telemetry():
    """Server-sent events endpoint for real-time telemetry"""
    def generate():
        # Mock real-time data stream
        import json
        import random
        
        while True:
            # Generate mock telemetry data
            mock_data = {
                'deviceId': f'DEVICE_{random.randint(1000, 9999)}',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'location': {
                    'lat': 20.2961 + random.uniform(-0.01, 0.01),
                    'lon': 85.8245 + random.uniform(-0.01, 0.01)
                },
                'speedKmph': random.uniform(30, 80),
                'acceleration': {
                    'x': random.uniform(-2, 2),
                    'y': random.uniform(-2, 2),
                    'z': random.uniform(9, 10)
                },
                'fuelLevel': random.uniform(20, 100)
            }
            
            yield f"data: {json.dumps(mock_data)}\n\n"
            time.sleep(1)
    
    return app.response_class(
        generate(),
        mimetype='text/plain',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

# Add toll events query endpoint
@app.route('/toll/events', methods=['GET'])
@require_permission('read')
def get_toll_events():
    """Get toll events with optional filtering"""
    try:
        device_id = request.args.get('device_id')
        limit = int(request.args.get('limit', 100))
        
        import sqlite3
        conn = sqlite3.connect('prototype.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if device_id:
            cursor.execute('''
                SELECT * FROM toll_events 
                WHERE device_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (device_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM toll_events 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
        
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch toll events: {e}")
        return jsonify({"error": "failed to fetch toll events"}), 500

if __name__ == "__main__":
    app.start_time = time.time()
    
    # Initialize WebSocket if available
    try:
        from websocket_enhanced import init_websocket
        websocket_manager = init_websocket(app)
        logger.info("WebSocket manager initialized")
    except ImportError:
        logger.warning("WebSocket manager not available")
    
    logger.info("Starting API server on port 5000")
    
    if 'websocket_manager' in locals():
        # Run with SocketIO support
        websocket_manager.socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    else:
        # Run without WebSocket support
        app.run(host='0.0.0.0', port=5000, debug=True)