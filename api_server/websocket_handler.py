#!/usr/bin/env python3
"""
WebSocket handler for real-time dashboard updates
"""

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import json
import logging
import redis
import threading
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Redis for pub/sub
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Connected clients
connected_clients = set()

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    connected_clients.add(request.sid)
    join_room('dashboard')
    
    # Send initial data
    emit('status', {
        'connected': True,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    connected_clients.discard(request.sid)
    leave_room('dashboard')

@socketio.on('subscribe_vehicle')
def handle_subscribe_vehicle(data):
    """Subscribe to specific vehicle updates"""
    vehicle_id = data.get('vehicle_id')
    if vehicle_id:
        join_room(f'vehicle_{vehicle_id}')
        logger.info(f"Client {request.sid} subscribed to vehicle {vehicle_id}")

def broadcast_telemetry(telemetry_data):
    """Broadcast telemetry data to dashboard"""
    try:
        socketio.emit('telemetry_update', telemetry_data, room='dashboard')
        
        # Also emit to specific vehicle room
        vehicle_id = telemetry_data.get('deviceId')
        if vehicle_id:
            socketio.emit('vehicle_update', telemetry_data, room=f'vehicle_{vehicle_id}')
            
    except Exception as e:
        logger.error(f"Broadcast telemetry error: {e}")

def broadcast_event(event_data):
    """Broadcast event data to dashboard"""
    try:
        socketio.emit('event_update', event_data, room='dashboard')
    except Exception as e:
        logger.error(f"Broadcast event error: {e}")

def broadcast_toll_event(toll_data):
    """Broadcast toll event to dashboard"""
    try:
        socketio.emit('toll_update', toll_data, room='dashboard')
    except Exception as e:
        logger.error(f"Broadcast toll error: {e}")

def redis_listener():
    """Listen for Redis pub/sub messages"""
    pubsub = redis_client.pubsub()
    pubsub.subscribe(['telemetry', 'events', 'tolls'])
    
    logger.info("Started Redis listener for real-time updates")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                channel = message['channel']
                
                if channel == 'telemetry':
                    broadcast_telemetry(data)
                elif channel == 'events':
                    broadcast_event(data)
                elif channel == 'tolls':
                    broadcast_toll_event(data)
                    
            except Exception as e:
                logger.error(f"Redis message processing error: {e}")

# Start Redis listener in background thread
def start_redis_listener():
    thread = threading.Thread(target=redis_listener, daemon=True)
    thread.start()

# Mock data generator for demo
def generate_mock_data():
    """Generate mock telemetry data for demo"""
    import random
    
    devices = ['DEVICE_001', 'DEVICE_002', 'DEVICE_003']
    
    while True:
        try:
            for device_id in devices:
                # Generate mock telemetry
                telemetry = {
                    'deviceId': device_id,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'location': {
                        'lat': 20.2961 + random.uniform(-0.01, 0.01),
                        'lon': 85.8245 + random.uniform(-0.01, 0.01)
                    },
                    'speedKmph': random.uniform(30, 80),
                    'heading': random.uniform(0, 360),
                    'acceleration': {
                        'x': random.uniform(-2, 2),
                        'y': random.uniform(-2, 2),
                        'z': random.uniform(8, 11)
                    }
                }
                
                # Publish to Redis
                redis_client.publish('telemetry', json.dumps(telemetry))
                
                # Occasionally generate events
                if random.random() < 0.1:
                    event = {
                        'deviceId': device_id,
                        'eventType': random.choice(['HARSH_BRAKE', 'HARSH_ACCEL', 'SPEEDING']),
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'location': telemetry['location'],
                        'severity': random.choice(['LOW', 'MEDIUM', 'HIGH'])
                    }
                    redis_client.publish('events', json.dumps(event))
                
                # Occasionally generate toll events
                if random.random() < 0.05:
                    toll = {
                        'deviceId': device_id,
                        'gantryId': random.randint(1, 5),
                        'amount': 0.05,
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'paid': True,
                        'txHash': f"0x{''.join(random.choices('0123456789abcdef', k=64))}"
                    }
                    redis_client.publish('tolls', json.dumps(toll))
            
            time.sleep(2)  # Update every 2 seconds
            
        except Exception as e:
            logger.error(f"Mock data generation error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    start_redis_listener()
    
    # Start mock data generator for demo
    mock_thread = threading.Thread(target=generate_mock_data, daemon=True)
    mock_thread.start()
    
    logger.info("Starting WebSocket server on port 5003")
    socketio.run(app, host='0.0.0.0', port=5003, debug=True)