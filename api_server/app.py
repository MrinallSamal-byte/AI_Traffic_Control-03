#!/usr/bin/env python3
"""
API Server - Main REST API for Smart Transportation System
Handles authentication, vehicle management, toll operations, and data access
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from cors_middleware import setup_cors
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import json
import uuid
import os
from datetime import datetime, timedelta
import hashlib
import requests
import logging
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_services.driver_score import predict_score
from db import db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Setup CORS for React frontend
setup_cors(app)
jwt = JWTManager(app)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'transport_system',
    'user': 'admin',
    'password': 'password'
}

# Redis configuration
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def get_db():
    """Get database connection"""
    if not hasattr(g, 'db'):
        g.db = psycopg2.connect(**DB_CONFIG)
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    if hasattr(g, 'db'):
        g.db.close()

# Authentication endpoints
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Simple authentication (in production, use proper password hashing)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            access_token = create_access_token(identity=str(user['user_id']))
            return jsonify({
                'access_token': access_token,
                'user': dict(user)
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """User registration"""
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        
        if not all([name, email]):
            return jsonify({'error': 'Name and email required'}), 400
        
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'error': 'User already exists'}), 409
        
        # Create user
        cursor.execute(
            "INSERT INTO users (name, email, phone) VALUES (%s, %s, %s) RETURNING *",
            (name, email, phone)
        )
        user = cursor.fetchone()
        conn.commit()
        
        access_token = create_access_token(identity=str(user['user_id']))
        
        return jsonify({
            'access_token': access_token,
            'user': dict(user)
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

# Device management endpoints
@app.route('/api/v1/devices/register', methods=['POST'])
@jwt_required()
def register_device():
    """Register OBU device"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        registration_no = data.get('registration_no')
        obu_device_id = data.get('obu_device_id')
        
        if not all([registration_no, obu_device_id]):
            return jsonify({'error': 'Registration number and device ID required'}), 400
        
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Create vehicle record
        cursor.execute("""
            INSERT INTO vehicles (user_id, registration_no, obu_device_id, wallet_address)
            VALUES (%s, %s, %s, %s) RETURNING *
        """, (user_id, registration_no, obu_device_id, f"0x{uuid.uuid4().hex[:40]}"))
        
        vehicle = cursor.fetchone()
        
        # Create wallet
        cursor.execute("""
            INSERT INTO wallets (vehicle_id, balance) VALUES (%s, %s)
        """, (vehicle['vehicle_id'], 100.00))  # Initial balance
        
        conn.commit()
        
        return jsonify({
            'vehicle': dict(vehicle),
            'provisioning_token': f"TOKEN_{uuid.uuid4().hex[:16]}"
        }), 201
        
    except Exception as e:
        logger.error(f"Device registration error: {e}")
        return jsonify({'error': 'Device registration failed'}), 500

@app.route('/api/v1/vehicles', methods=['GET'])
@jwt_required()
def get_vehicles():
    """Get user's vehicles"""
    try:
        user_id = get_jwt_identity()
        
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT v.*, w.balance, w.currency 
            FROM vehicles v
            LEFT JOIN wallets w ON v.vehicle_id = w.vehicle_id
            WHERE v.user_id = %s
        """, (user_id,))
        
        vehicles = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({'vehicles': vehicles})
        
    except Exception as e:
        logger.error(f"Get vehicles error: {e}")
        return jsonify({'error': 'Failed to get vehicles'}), 500

# Telemetry endpoints
@app.route('/api/v1/telemetry', methods=['POST'])
def receive_telemetry():
    """Receive telemetry data (for non-MQTT clients)"""
    try:
        data = request.get_json()
        device_id = data.get('deviceId')
        
        if not device_id:
            return jsonify({'error': 'Device ID required'}), 400
        
        # Store in Redis for real-time access
        redis_client.setex(
            f"latest_telemetry:{device_id}",
            300,  # 5 minutes TTL
            json.dumps(data)
        )
        
        return jsonify({'status': 'received'}), 200
        
    except Exception as e:
        logger.error(f"Telemetry error: {e}")
        return jsonify({'error': 'Failed to process telemetry'}), 500

@app.route('/api/v1/vehicles/<vehicle_id>/telemetry', methods=['GET'])
@jwt_required()
def get_vehicle_telemetry(vehicle_id):
    """Get vehicle telemetry history"""
    try:
        user_id = get_jwt_identity()
        hours = request.args.get('hours', 1, type=int)
        
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verify vehicle ownership
        cursor.execute("""
            SELECT obu_device_id FROM vehicles 
            WHERE vehicle_id = %s AND user_id = %s
        """, (vehicle_id, user_id))
        
        vehicle = cursor.fetchone()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        # Get telemetry data
        cursor.execute("""
            SELECT * FROM telemetry 
            WHERE device_id = %s AND time >= NOW() - INTERVAL '%s hours'
            ORDER BY time DESC
            LIMIT 1000
        """, (vehicle['obu_device_id'], hours))
        
        telemetry = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'telemetry': telemetry,
            'count': len(telemetry)
        })
        
    except Exception as e:
        logger.error(f"Get telemetry error: {e}")
        return jsonify({'error': 'Failed to get telemetry'}), 500

# Driver scoring endpoints
@app.route('/api/v1/vehicles/<vehicle_id>/score', methods=['GET'])
@jwt_required()
def get_driver_score(vehicle_id):
    """Get latest driver score"""
    try:
        user_id = get_jwt_identity()
        
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verify vehicle ownership
        cursor.execute("""
            SELECT obu_device_id FROM vehicles 
            WHERE vehicle_id = %s AND user_id = %s
        """, (vehicle_id, user_id))
        
        vehicle = cursor.fetchone()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        # Get latest score from ML service
        try:
            response = requests.get(f"http://localhost:5001/score/{vehicle['obu_device_id']}")
            if response.status_code == 200:
                score_data = response.json()
            else:
                score_data = {'error': 'ML service unavailable'}
        except:
            score_data = {'error': 'ML service unavailable'}
        
        # Get historical scores
        cursor.execute("""
            SELECT * FROM driver_scores 
            WHERE vehicle_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 10
        """, (vehicle_id,))
        
        historical_scores = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'current_score': score_data,
            'historical_scores': historical_scores
        })
        
    except Exception as e:
        logger.error(f"Get driver score error: {e}")
        return jsonify({'error': 'Failed to get driver score'}), 500

# Traffic and prediction endpoints
@app.route('/api/v1/traffic/prediction', methods=['GET'])
def get_traffic_prediction():
    """Get traffic prediction for road segment"""
    try:
        segment_id = request.args.get('segment')
        horizon = request.args.get('horizon', '30m')
        
        if not segment_id:
            return jsonify({'error': 'Segment ID required'}), 400
        
        # Mock prediction data (in production, call ML service)
        prediction = {
            'segment_id': segment_id,
            'horizon': horizon,
            'predicted_speed': 45.2,
            'confidence': 0.85,
            'congestion_level': 'moderate',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify(prediction)
        
    except Exception as e:
        logger.error(f"Traffic prediction error: {e}")
        return jsonify({'error': 'Failed to get prediction'}), 500

# Toll management endpoints
@app.route('/api/v1/toll/gantries', methods=['GET'])
def get_toll_gantries():
    """Get all toll gantries"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM toll_gantries ORDER BY name")
        gantries = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({'gantries': gantries})
        
    except Exception as e:
        logger.error(f"Get gantries error: {e}")
        return jsonify({'error': 'Failed to get gantries'}), 500

@app.route('/api/v1/toll/charge', methods=['POST'])
def charge_toll():
    """Process toll charge"""
    try:
        data = request.get_json()
        vehicle_id = data.get('vehicleId')
        gantry_id = data.get('gantryId')
        calculated_price = data.get('calculatedPrice')
        
        if not all([vehicle_id, gantry_id, calculated_price]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check wallet balance
        cursor.execute("""
            SELECT balance FROM wallets WHERE vehicle_id = %s
        """, (vehicle_id,))
        
        wallet = cursor.fetchone()
        if not wallet or wallet['balance'] < calculated_price:
            return jsonify({'error': 'Insufficient balance'}), 402
        
        # Create toll transaction
        tx_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO toll_transactions 
            (tx_id, vehicle_id, gantry_id, entry_time, price, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (tx_id, vehicle_id, gantry_id, datetime.utcnow(), calculated_price, 'completed'))
        
        # Update wallet balance
        cursor.execute("""
            UPDATE wallets SET balance = balance - %s WHERE vehicle_id = %s
        """, (calculated_price, vehicle_id))
        
        conn.commit()
        
        return jsonify({
            'transaction_id': tx_id,
            'status': 'completed',
            'amount_charged': calculated_price
        })
        
    except Exception as e:
        logger.error(f"Toll charge error: {e}")
        return jsonify({'error': 'Failed to process toll charge'}), 500

@app.route('/api/v1/vehicles/<vehicle_id>/transactions', methods=['GET'])
@jwt_required()
def get_vehicle_transactions(vehicle_id):
    """Get vehicle toll transactions"""
    try:
        user_id = get_jwt_identity()
        
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verify vehicle ownership
        cursor.execute("""
            SELECT vehicle_id FROM vehicles 
            WHERE vehicle_id = %s AND user_id = %s
        """, (vehicle_id, user_id))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Vehicle not found'}), 404
        
        # Get transactions
        cursor.execute("""
            SELECT t.*, g.name as gantry_name 
            FROM toll_transactions t
            JOIN toll_gantries g ON t.gantry_id = g.gantry_id
            WHERE t.vehicle_id = %s 
            ORDER BY t.created_at DESC
            LIMIT 50
        """, (vehicle_id,))
        
        transactions = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({'transactions': transactions})
        
    except Exception as e:
        logger.error(f"Get transactions error: {e}")
        return jsonify({'error': 'Failed to get transactions'}), 500

# Admin endpoints
@app.route('/api/v1/admin/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    """Get active alerts and incidents"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get recent events
        cursor.execute("""
            SELECT e.*, v.registration_no 
            FROM events e
            LEFT JOIN vehicles v ON e.device_id = v.obu_device_id
            WHERE e.created_at >= NOW() - INTERVAL '1 hour'
            ORDER BY e.created_at DESC
            LIMIT 100
        """, )
        
        events = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({'alerts': events})
        
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return jsonify({'error': 'Failed to get alerts'}), 500

@app.route('/api/v1/admin/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_data():
    """Get dashboard summary data"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get summary statistics
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM vehicles) as total_vehicles,
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM toll_transactions WHERE created_at >= CURRENT_DATE) as daily_transactions,
                (SELECT SUM(price) FROM toll_transactions WHERE created_at >= CURRENT_DATE) as daily_revenue
        """)
        
        stats = cursor.fetchone()
        
        # Get recent activity
        cursor.execute("""
            SELECT device_id, COUNT(*) as message_count
            FROM telemetry 
            WHERE time >= NOW() - INTERVAL '1 hour'
            GROUP BY device_id
            ORDER BY message_count DESC
            LIMIT 10
        """)
        
        active_devices = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'statistics': dict(stats),
            'active_devices': active_devices
        })
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'error': 'Failed to get dashboard data'}), 500

@app.route('/driver_score', methods=['POST'])
def driver_score():
    """Calculate driver score from telemetry data"""
    try:
        telemetry = request.get_json(force=True)
        if telemetry is None:
            return jsonify({"error": "invalid json"}), 400
    except Exception as json_error:
        return jsonify({"error": "invalid json"}), 400
    
    try:
        
        # Validate required fields
        required_fields = ['device_id', 'timestamp']
        for field in required_fields:
            if field not in telemetry:
                return jsonify({"error": f"missing field: {field}"}), 400
        
        # Get driver score from ML service
        score_result = predict_score(telemetry)
        
        # Store in database
        try:
            db_manager.insert_telemetry_and_score(telemetry, score_result)
        except Exception as db_error:
            logger.warning(f"Database storage failed: {db_error}")
        
        response = {
            "device_id": telemetry.get("device_id"),
            "timestamp": telemetry.get("timestamp"),
            "driver_score": score_result["score"],
            "model": score_result["model"]
        }
        return jsonify(response)
    except Exception as e:
        logger.exception("driver_score error")
        return jsonify({"error": "internal error", "detail": str(e)}), 500

@app.route('/scores', methods=['GET'])
def get_scores():
    """Get recent driver scores"""
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)  # Cap at 100
        
        scores = db_manager.get_recent_scores(limit)
        return jsonify({"scores": scores, "count": len(scores)})
    except Exception as e:
        logger.exception("get_scores error")
        return jsonify({"error": "failed to get scores", "detail": str(e)}), 500

# Health check
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'api_server',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })

if __name__ == "__main__":
    # Initialize database connection
    try:
        db_manager.connect()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)