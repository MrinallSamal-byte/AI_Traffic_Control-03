#!/usr/bin/env python3
"""
WebSocket Manager for Real-time Dashboard Streaming
"""

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading
import time
import queue
import redis
from collections import defaultdict
import jwt

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and real-time data streaming"""
    
    def __init__(self, app: Flask = None, redis_client=None):
        self.app = app
        self.socketio = None
        self.redis_client = redis_client
        self.connected_clients = {}
        self.room_subscriptions = defaultdict(set)
        self.message_queue = queue.Queue()
        self.streaming_thread = None
        self.is_streaming = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize WebSocket manager with Flask app"""
        self.app = app
        
        # Initialize SocketIO
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='threading',
            logger=True,
            engineio_logger=True
        )
        
        # Initialize Redis if not provided
        if not self.redis_client:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    decode_responses=True
                )
                self.redis_client.ping()  # Test connection
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory storage.")
                self.redis_client = None
        
        # Register event handlers
        self._register_handlers()
        
        # Start streaming thread
        self._start_streaming_thread()
        
        logger.info("WebSocket manager initialized")
    
    def _register_handlers(self):
        """Register SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """Handle client connection"""
            client_id = self._get_client_id()
            
            # Authenticate client if auth provided
            auth_info = None
            if auth and 'token' in auth:
                auth_info = self._authenticate_token(auth['token'])
                if not auth_info:
                    logger.warning(f"Client {client_id} authentication failed")
                    disconnect()
                    return False
            
            # Store client info
            self.connected_clients[client_id] = {
                'connected_at': datetime.utcnow().isoformat(),
                'auth_info': auth_info,
                'subscriptions': set(),
                'last_activity': datetime.utcnow()
            }
            
            logger.info(f"Client {client_id} connected")
            
            # Send welcome message
            emit('connection_status', {
                'status': 'connected',
                'client_id': client_id,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'authenticated': auth_info is not None
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            client_id = self._get_client_id()
            
            if client_id in self.connected_clients:
                # Leave all rooms
                client_info = self.connected_clients[client_id]
                for room in client_info['subscriptions']:
                    leave_room(room)
                    self.room_subscriptions[room].discard(client_id)
                
                # Remove client
                del self.connected_clients[client_id]
                
                logger.info(f"Client {client_id} disconnected")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle subscription to data streams"""
            client_id = self._get_client_id()
            
            if client_id not in self.connected_clients:
                emit('error', {'message': 'Client not registered'})
                return
            
            stream_type = data.get('stream_type')
            filters = data.get('filters', {})
            
            if not stream_type:
                emit('error', {'message': 'stream_type required'})
                return
            
            # Check permissions
            if not self._check_stream_permission(client_id, stream_type):
                emit('error', {'message': 'Permission denied for stream'})
                return
            
            # Create room name
            room_name = self._create_room_name(stream_type, filters)
            
            # Join room
            join_room(room_name)
            self.connected_clients[client_id]['subscriptions'].add(room_name)
            self.room_subscriptions[room_name].add(client_id)
            
            logger.info(f"Client {client_id} subscribed to {room_name}")
            
            emit('subscription_status', {
                'stream_type': stream_type,
                'room': room_name,
                'status': 'subscribed',
                'filters': filters
            })
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Handle unsubscription from data streams"""
            client_id = self._get_client_id()
            
            if client_id not in self.connected_clients:
                return
            
            stream_type = data.get('stream_type')
            filters = data.get('filters', {})
            room_name = self._create_room_name(stream_type, filters)
            
            # Leave room
            leave_room(room_name)
            self.connected_clients[client_id]['subscriptions'].discard(room_name)
            self.room_subscriptions[room_name].discard(client_id)
            
            logger.info(f"Client {client_id} unsubscribed from {room_name}")
            
            emit('subscription_status', {
                'stream_type': stream_type,
                'room': room_name,
                'status': 'unsubscribed'
            })
        
        @self.socketio.on('get_status')
        def handle_get_status():
            """Get connection and subscription status"""
            client_id = self._get_client_id()
            
            if client_id in self.connected_clients:
                client_info = self.connected_clients[client_id]
                emit('status', {
                    'client_id': client_id,
                    'connected_at': client_info['connected_at'],
                    'authenticated': client_info['auth_info'] is not None,
                    'subscriptions': list(client_info['subscriptions']),
                    'total_clients': len(self.connected_clients)
                })
    
    def _get_client_id(self) -> str:
        """Get unique client ID from session"""
        from flask_socketio import request
        return request.sid
    
    def _authenticate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate JWT token"""
        try:
            from flask import current_app
            payload = jwt.decode(
                token,
                current_app.config.get('JWT_SECRET_KEY', 'default-secret'),
                algorithms=['HS256']
            )
            return {
                'user': payload.get('sub'),
                'permissions': payload.get('permissions', []),
                'role': payload.get('role')
            }
        except jwt.InvalidTokenError:
            return None
    
    def _check_stream_permission(self, client_id: str, stream_type: str) -> bool:
        """Check if client has permission for stream type"""
        client_info = self.connected_clients.get(client_id, {})
        auth_info = client_info.get('auth_info')
        
        # If not authenticated, allow basic streams only
        if not auth_info:
            return stream_type in ['telemetry', 'vehicle_status']
        
        # Check permissions based on stream type
        permissions = auth_info.get('permissions', [])
        
        stream_permissions = {
            'telemetry': ['read'],
            'vehicle_status': ['read'],
            'toll_events': ['read'],
            'ml_predictions': ['read'],
            'system_alerts': ['admin'],
            'debug_logs': ['admin']
        }
        
        required_perms = stream_permissions.get(stream_type, ['admin'])
        return any(perm in permissions for perm in required_perms)
    
    def _create_room_name(self, stream_type: str, filters: Dict[str, Any]) -> str:
        """Create room name from stream type and filters"""
        if not filters:
            return f"stream_{stream_type}"
        
        # Sort filters for consistent room names
        filter_str = "_".join(f"{k}_{v}" for k, v in sorted(filters.items()))
        return f"stream_{stream_type}_{filter_str}"
    
    def _start_streaming_thread(self):
        """Start background thread for processing streaming data"""
        if self.streaming_thread and self.streaming_thread.is_alive():
            return
        
        self.is_streaming = True
        self.streaming_thread = threading.Thread(target=self._streaming_worker, daemon=True)
        self.streaming_thread.start()
        logger.info("Streaming thread started")
    
    def _streaming_worker(self):
        """Background worker for processing streaming messages"""
        while self.is_streaming:
            try:
                # Process queued messages
                while not self.message_queue.empty():
                    try:
                        message = self.message_queue.get_nowait()
                        self._process_streaming_message(message)
                    except queue.Empty:
                        break
                
                # Check for Redis messages if available
                if self.redis_client:
                    self._check_redis_messages()
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Streaming worker error: {e}")
                time.sleep(1)
    
    def _check_redis_messages(self):
        """Check for messages from Redis pub/sub"""
        try:
            # This would implement Redis pub/sub listening
            # For now, we'll skip this implementation
            pass
        except Exception as e:
            logger.error(f"Redis message check failed: {e}")
    
    def _process_streaming_message(self, message: Dict[str, Any]):
        """Process and broadcast streaming message"""
        try:
            stream_type = message.get('stream_type')
            data = message.get('data')
            filters = message.get('filters', {})
            
            if not stream_type or not data:
                return
            
            # Create room name
            room_name = self._create_room_name(stream_type, filters)
            
            # Broadcast to room if there are subscribers
            if room_name in self.room_subscriptions and self.room_subscriptions[room_name]:
                self.socketio.emit('stream_data', {
                    'stream_type': stream_type,
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'filters': filters
                }, room=room_name)
                
                logger.debug(f"Broadcasted {stream_type} to {len(self.room_subscriptions[room_name])} clients")
        
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    # Public methods for broadcasting data
    
    def broadcast_telemetry(self, telemetry_data: Dict[str, Any], device_id: str = None):
        """Broadcast telemetry data"""
        filters = {'device_id': device_id} if device_id else {}
        
        message = {
            'stream_type': 'telemetry',
            'data': telemetry_data,
            'filters': filters
        }
        
        self.message_queue.put(message)
    
    def broadcast_vehicle_status(self, status_data: Dict[str, Any], device_id: str = None):
        """Broadcast vehicle status update"""
        filters = {'device_id': device_id} if device_id else {}
        
        message = {
            'stream_type': 'vehicle_status',
            'data': status_data,
            'filters': filters
        }
        
        self.message_queue.put(message)
    
    def broadcast_toll_event(self, toll_data: Dict[str, Any]):
        """Broadcast toll event"""
        message = {
            'stream_type': 'toll_events',
            'data': toll_data,
            'filters': {}
        }
        
        self.message_queue.put(message)
    
    def broadcast_ml_prediction(self, prediction_data: Dict[str, Any], device_id: str = None):
        """Broadcast ML prediction result"""
        filters = {'device_id': device_id} if device_id else {}
        
        message = {
            'stream_type': 'ml_predictions',
            'data': prediction_data,
            'filters': filters
        }
        
        self.message_queue.put(message)
    
    def broadcast_system_alert(self, alert_data: Dict[str, Any]):
        """Broadcast system alert"""
        message = {
            'stream_type': 'system_alerts',
            'data': alert_data,
            'filters': {}
        }
        
        self.message_queue.put(message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            'total_clients': len(self.connected_clients),
            'authenticated_clients': sum(
                1 for client in self.connected_clients.values()
                if client['auth_info'] is not None
            ),
            'total_rooms': len(self.room_subscriptions),
            'active_rooms': len([
                room for room, clients in self.room_subscriptions.items()
                if clients
            ]),
            'message_queue_size': self.message_queue.qsize(),
            'streaming_active': self.is_streaming
        }
    
    def cleanup_inactive_clients(self, timeout_minutes: int = 30):
        """Clean up inactive clients"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        inactive_clients = []
        
        for client_id, client_info in self.connected_clients.items():
            if client_info['last_activity'] < cutoff_time:
                inactive_clients.append(client_id)
        
        for client_id in inactive_clients:
            # This would normally be handled by disconnect event
            # but we can clean up manually if needed
            logger.info(f"Cleaning up inactive client: {client_id}")
    
    def stop_streaming(self):
        """Stop the streaming thread"""
        self.is_streaming = False
        if self.streaming_thread:
            self.streaming_thread.join(timeout=5)
        logger.info("Streaming stopped")

# Global WebSocket manager instance
websocket_manager = None

def init_websocket_manager(app: Flask, redis_client=None) -> WebSocketManager:
    """Initialize WebSocket manager"""
    global websocket_manager
    websocket_manager = WebSocketManager(app, redis_client)
    return websocket_manager

def get_websocket_manager() -> Optional[WebSocketManager]:
    """Get the global WebSocket manager instance"""
    return websocket_manager

if __name__ == "__main__":
    # Test the WebSocket manager
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'
    
    ws_manager = init_websocket_manager(app)
    
    @app.route('/test_broadcast')
    def test_broadcast():
        # Test broadcasting some data
        ws_manager.broadcast_telemetry({
            'deviceId': 'TEST_DEVICE',
            'speed': 65.5,
            'location': {'lat': 20.2961, 'lon': 85.8245}
        }, device_id='TEST_DEVICE')
        
        return {'status': 'broadcast sent'}
    
    print("WebSocket manager test setup complete")
    print("Run with: python websocket_manager.py")
    
    if __name__ == "__main__":
        ws_manager.socketio.run(app, host='0.0.0.0', port=5001, debug=True)