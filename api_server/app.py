#!/usr/bin/env python3
"""
API Server - MVP Prototype for Smart Transportation System
Simplified version with essential endpoints for ML model demo
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
import sys
from datetime import datetime, timedelta
import logging
import time
import psutil
from collections import defaultdict

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
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change in production
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# Metrics tracking
metrics = {
    'request_count': defaultdict(int),
    'error_count': defaultdict(int),
    'response_times': defaultdict(list)
}

# Simple auth middleware
@app.before_request
def track_metrics():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    duration = time.time() - request.start_time
    endpoint = request.endpoint or 'unknown'
    
    # Track metrics
    metrics['request_count'][endpoint] += 1
    metrics['response_times'][endpoint].append(duration)
    
    if response.status_code >= 400:
        metrics['error_count'][endpoint] += 1
    
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
def get_metrics():
    """Get basic metrics"""
    return jsonify({
        'request_count': dict(metrics['request_count']),
        'error_count': dict(metrics['error_count']),
        'avg_response_time': {
            endpoint: sum(times) / len(times) if times else 0
            for endpoint, times in metrics['response_times'].items()
        }
    })

# Authentication endpoints
@app.route('/auth/login', methods=['POST'])
def login():
    """Simple login endpoint"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Simple auth (use proper auth in production)
    if username == 'admin' and password == 'password':
        access_token = create_access_token(identity=username)
        return jsonify({'access_token': access_token})
    
    return jsonify({'error': 'Invalid credentials'}), 401

# Toll detection and charging
@app.route('/toll/charge', methods=['POST'])
@jwt_required()
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
        blockchain_response = requests.post('http://localhost:5002/toll/autopay', json={
            'vehicle_address': vehicle_address,
            'gantry_id': data['gantry_id'],
            'amount': toll_amount
        }, timeout=10)
        
        if blockchain_response.status_code == 200:
            blockchain_data = blockchain_response.json()
            
            # Log toll event
            logger.info(f"Toll charged", extra={
                'device_id': data['device_id'],
                'gantry_id': data['gantry_id'],
                'amount': toll_amount,
                'toll_id': blockchain_data.get('toll_id'),
                'tx_hash': blockchain_data.get('tx_hash'),
                'paid': blockchain_data.get('paid', False)
            })
            
            return jsonify({
                'device_id': data['device_id'],
                'gantry_id': data['gantry_id'],
                'amount': toll_amount,
                'toll_id': blockchain_data.get('toll_id'),
                'tx_hash': blockchain_data.get('tx_hash'),
                'paid': blockchain_data.get('paid', False),
                'timestamp': data['timestamp']
            })
        else:
            logger.error(f"Blockchain toll charge failed: {blockchain_response.text}")
            return jsonify({"error": "toll charge failed"}), 500
            
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

# Driver scoring endpoint
@app.route('/driver_score', methods=['POST'])
@jwt_required()
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

if __name__ == "__main__":
    app.start_time = time.time()
    logger.info("Starting API server on port 5000")
    app.run(host='0.0.0.0', port=5000, debug=True)