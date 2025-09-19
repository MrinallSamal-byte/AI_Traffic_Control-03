#!/usr/bin/env python3
"""
WebSocket Server for Real-time Updates
Provides live data streaming to the React frontend
"""

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import json
import time
import threading
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Database and Redis connections
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'transport_system',
    'user': 'admin',
    'password': 'password'
}

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

class LiveDataStreamer:
    def __init__(self):
        self.active_connections = set()
        self.streaming = False
        
    def start_streaming(self):
        """Start the live data streaming thread"""
        if not self.streaming:
            self.streaming = True
            thread = threading.Thread(target=self._stream_loop)
            thread.daemon = True
            thread.start()
            logger.info("✓ Live data streaming started")
    
    def _stream_loop(self):
        """Main streaming loop"""
        while self.streaming:
            try:
                # Get live telemetry data
                live_data = self._get_live_telemetry()
                if live_data:
                    socketio.emit('live_telemetry', live_data, room='dashboard')
                
                # Get system metrics
                system_metrics = self._get_system_metrics()
                if system_metrics:
                    socketio.emit('system_metrics', system_metrics, room='admin')
                
                # Get recent events
                events = self._get_recent_events()
                if events:
                    socketio.emit('live_events', events, room='dashboard')
                
                time.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                time.sleep(5)
    
    def _get_live_telemetry(self):
        """Get latest telemetry data from Redis"""
        try:
            # Get all active device positions
            devices = []
            for key in redis_client.scan_iter(match="position:*"):
                device_id = key.split(':')[1]
                position_data = redis_client.get(key)
                if position_data:
                    data = json.loads(position_data)
                    data['deviceId'] = device_id
                    devices.append(data)
            
            return {
                'timestamp': time.time(),
                'devices': devices,
                'count': len(devices)
            }
        except Exception as e:
            logger.error(f"Error getting live telemetry: {e}")
            return None
    
    def _get_system_metrics(self):
        """Get system performance metrics"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get active vehicle count
            cursor.execute("""
                SELECT COUNT(DISTINCT device_id) as active_vehicles
                FROM telemetry 
                WHERE time >= NOW() - INTERVAL '5 minutes'
            """)
            active_vehicles = cursor.fetchone()['active_vehicles']
            
            # Get recent transaction count
            cursor.execute("""
                SELECT COUNT(*) as daily_transactions,
                       COALESCE(SUM(price), 0) as daily_revenue
                FROM toll_transactions 
                WHERE created_at >= CURRENT_DATE
            """)
            transaction_data = cursor.fetchone()
            
            # Get recent events count
            cursor.execute("""
                SELECT COUNT(*) as recent_events
                FROM events 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
            """)
            events_count = cursor.fetchone()['recent_events']
            
            cursor.close()
            conn.close()
            
            return {
                'timestamp': time.time(),
                'active_vehicles': active_vehicles,
                'daily_transactions': transaction_data['daily_transactions'],
                'daily_revenue': float(transaction_data['daily_revenue']),
                'recent_events': events_count,
                'avg_network_speed': 62 + (time.time() % 10 - 5)  # Simulated
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return None
    
    def _get_recent_events(self):
        """Get recent driving events"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT e.*, v.registration_no 
                FROM events e
                LEFT JOIN vehicles v ON e.device_id = v.obu_device_id
                WHERE e.created_at >= NOW() - INTERVAL '10 minutes'
                ORDER BY e.created_at DESC
                LIMIT 10
            """)
            
            events = [dict(row) for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return {
                'timestamp': time.time(),
                'events': events
            }
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return None

# Initialize streamer
streamer = LiveDataStreamer()

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    streamer.active_connections.add(request.sid)
    
    # Start streaming if this is the first connection
    if len(streamer.active_connections) == 1:
        streamer.start_streaming()
    
    emit('connection_status', {'status': 'connected', 'timestamp': time.time()})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    streamer.active_connections.discard(request.sid)

@socketio.on('join_room')
def handle_join_room(data):
    """Handle room joining for targeted updates"""
    room = data.get('room', 'dashboard')
    join_room(room)
    logger.info(f"Client {request.sid} joined room: {room}")
    emit('room_joined', {'room': room, 'timestamp': time.time()})

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle room leaving"""
    room = data.get('room', 'dashboard')
    leave_room(room)
    logger.info(f"Client {request.sid} left room: {room}")

@socketio.on('request_vehicle_data')
def handle_vehicle_data_request(data):
    """Handle specific vehicle data requests"""
    try:
        device_id = data.get('device_id')
        if not device_id:
            emit('error', {'message': 'Device ID required'})
            return
        
        # Get vehicle telemetry from database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM telemetry 
            WHERE device_id = %s 
            AND time >= NOW() - INTERVAL '1 hour'
            ORDER BY time DESC
            LIMIT 100
        """, (device_id,))
        
        telemetry = [dict(row) for row in cursor.fetchall()]
        
        # Get latest position from Redis
        position_key = f"position:{device_id}"
        position_data = redis_client.get(position_key)
        current_position = json.loads(position_data) if position_data else None
        
        cursor.close()
        conn.close()
        
        emit('vehicle_data', {
            'device_id': device_id,
            'telemetry': telemetry,
            'current_position': current_position,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error handling vehicle data request: {e}")
        emit('error', {'message': 'Failed to get vehicle data'})

@socketio.on('request_admin_stats')
def handle_admin_stats_request():
    """Handle admin dashboard statistics request"""
    try:
        stats = streamer._get_system_metrics()
        if stats:
            emit('admin_stats', stats)
        else:
            emit('error', {'message': 'Failed to get admin statistics'})
    except Exception as e:
        logger.error(f"Error handling admin stats request: {e}")
        emit('error', {'message': 'Failed to get admin statistics'})

# REST endpoints for WebSocket management
@app.route('/ws/health', methods=['GET'])
def websocket_health():
    """WebSocket server health check"""
    return {
        'status': 'healthy',
        'active_connections': len(streamer.active_connections),
        'streaming': streamer.streaming,
        'timestamp': time.time()
    }

@app.route('/ws/broadcast', methods=['POST'])
def broadcast_message():
    """Broadcast message to all connected clients"""
    try:
        from flask import request
        data = request.get_json()
        
        message_type = data.get('type', 'notification')
        message_data = data.get('data', {})
        room = data.get('room', 'dashboard')
        
        socketio.emit(message_type, message_data, room=room)
        
        return {
            'status': 'success',
            'message': 'Broadcast sent',
            'recipients': len(streamer.active_connections)
        }
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return {'status': 'error', 'message': str(e)}, 500

if __name__ == '__main__':
    logger.info("🌐 Starting WebSocket server...")
    socketio.run(app, host='0.0.0.0', port=5003, debug=True)