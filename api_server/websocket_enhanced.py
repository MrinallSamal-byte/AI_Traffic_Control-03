#!/usr/bin/env python3
"""
Enhanced WebSocket Server for Real-time Dashboard Updates
Supports vehicle tracking, event streaming, and live telemetry
"""

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Set, Any, Optional
from collections import defaultdict, deque
import redis
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and real-time data streaming"""
    
    def __init__(self, app: Flask, redis_client=None, db_config=None):
        self.app = app
        self.socketio = SocketIO(
            app, 
            cors_allowed_origins="*",
            async_mode='threading',
            logger=True,
            engineio_logger=True
        )
        
        # Connection tracking
        self.connected_clients: Dict[str, Dict[str, Any]] = {}
        self.room_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Data caches
        self.vehicle_positions: Dict[str, Dict[str, Any]] = {}
        self.recent_events: deque = deque(maxlen=1000)
        self.live_metrics: Dict[str, Any] = {}
        
        # External connections
        self.redis_client = redis_client
        self.db_config = db_config
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _setup_event_handlers(self):
        """Setup WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """Handle client connection"""
            try:
                # Authenticate client
                client_info = self._authenticate_client(auth)
                if not client_info:
                    logger.warning(f"Unauthorized connection attempt from {request.sid}")
                    disconnect()
                    return False
                
                # Store client info
                self.connected_clients[request.sid] = {
                    'user': client_info['username'],
                    'role': client_info['role'],
                    'connected_at': datetime.utcnow().isoformat(),
                    'subscriptions': set()
                }
                
                logger.info(f"Client connected: {client_info['username']} ({request.sid})")
                
                # Send initial data
                emit('connection_status', {
                    'status': 'connected',
                    'user': client_info['username'],
                    'role': client_info['role'],
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Send current vehicle positions
                emit('vehicle_positions', list(self.vehicle_positions.values()))
                
                # Send recent events
                emit('recent_events', list(self.recent_events))
                
                return True
                
            except Exception as e:
                logger.error(f"Connection error: {e}")
                disconnect()
                return False
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            if request.sid in self.connected_clients:
                client = self.connected_clients[request.sid]
                logger.info(f"Client disconnected: {client['user']} ({request.sid})")
                
                # Remove from all rooms
                for subscription in client['subscriptions']:
                    self.room_subscriptions[subscription].discard(request.sid)
                
                del self.connected_clients[request.sid]
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle subscription to data streams"""
            if request.sid not in self.connected_clients:
                return
            
            subscription_type = data.get('type')
            params = data.get('params', {})
            
            if subscription_type == 'vehicle_tracking':
                self._subscribe_vehicle_tracking(request.sid, params)
            elif subscription_type == 'events':
                self._subscribe_events(request.sid, params)
            elif subscription_type == 'metrics':
                self._subscribe_metrics(request.sid, params)
            else:
                emit('error', {'message': f'Unknown subscription type: {subscription_type}'})
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Handle unsubscription from data streams"""
            if request.sid not in self.connected_clients:
                return
            
            subscription_type = data.get('type')
            room_name = f"{subscription_type}_{request.sid}"
            
            leave_room(room_name)
            self.room_subscriptions[room_name].discard(request.sid)
            self.connected_clients[request.sid]['subscriptions'].discard(room_name)
            
            emit('unsubscribed', {'type': subscription_type})
    
    def _authenticate_client(self, auth) -> Optional[Dict[str, Any]]:
        """Authenticate WebSocket client using JWT token"""
        if not auth or 'token' not in auth:
            return None
        
        try:
            from flask_jwt_extended import decode_token
            decoded_token = decode_token(auth['token'])
            
            return {
                'username': decoded_token['sub'],
                'role': decoded_token.get('role', 'viewer'),
                'permissions': decoded_token.get('permissions', [])
            }
        except Exception as e:
            logger.error(f"Token authentication failed: {e}")
            return None
    
    def _subscribe_vehicle_tracking(self, client_id: str, params: Dict[str, Any]):
        """Subscribe client to vehicle tracking updates"""
        room_name = f"vehicle_tracking_{client_id}"
        join_room(room_name)
        
        self.room_subscriptions[room_name].add(client_id)
        self.connected_clients[client_id]['subscriptions'].add(room_name)
        
        # Send current positions
        device_filter = params.get('devices', [])
        positions = self.vehicle_positions.values()
        
        if device_filter:
            positions = [pos for pos in positions if pos['deviceId'] in device_filter]
        
        emit('vehicle_positions', list(positions), room=room_name)
        emit('subscribed', {'type': 'vehicle_tracking', 'params': params})
    
    def _subscribe_events(self, client_id: str, params: Dict[str, Any]):
        """Subscribe client to event updates"""
        room_name = f"events_{client_id}"
        join_room(room_name)
        
        self.room_subscriptions[room_name].add(client_id)
        self.connected_clients[client_id]['subscriptions'].add(room_name)
        
        # Send recent events
        event_types = params.get('event_types', [])
        events = list(self.recent_events)
        
        if event_types:
            events = [event for event in events if event.get('type') in event_types]
        
        emit('recent_events', events, room=room_name)
        emit('subscribed', {'type': 'events', 'params': params})
    
    def _subscribe_metrics(self, client_id: str, params: Dict[str, Any]):
        """Subscribe client to metrics updates"""
        room_name = f"metrics_{client_id}"
        join_room(room_name)
        
        self.room_subscriptions[room_name].add(client_id)
        self.connected_clients[client_id]['subscriptions'].add(room_name)
        
        emit('live_metrics', self.live_metrics, room=room_name)
        emit('subscribed', {'type': 'metrics', 'params': params})
    
    def _start_background_tasks(self):
        """Start background tasks for data streaming"""
        
        def kafka_consumer_task():
            """Consume Kafka messages and broadcast to WebSocket clients"""
            try:
                consumer = KafkaConsumer(
                    'transport.telemetry',
                    'transport.events',
                    bootstrap_servers=['localhost:9092'],
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    group_id='websocket_consumer'
                )
                
                for message in consumer:
                    self._process_kafka_message(message)
                    
            except Exception as e:
                logger.error(f"Kafka consumer error: {e}")
        
        def metrics_update_task():
            """Periodically update and broadcast metrics"""
            while True:
                try:
                    self._update_live_metrics()
                    time.sleep(5)  # Update every 5 seconds
                except Exception as e:
                    logger.error(f"Metrics update error: {e}")
                    time.sleep(10)
        
        # Start background threads
        kafka_thread = threading.Thread(target=kafka_consumer_task, daemon=True)
        kafka_thread.start()
        
        metrics_thread = threading.Thread(target=metrics_update_task, daemon=True)
        metrics_thread.start()
        
        logger.info("Background tasks started")
    
    def _process_kafka_message(self, message):
        """Process Kafka message and broadcast to relevant clients"""
        topic = message.topic
        data = message.value
        
        if topic == 'transport.telemetry':
            self._handle_telemetry_update(data)
        elif topic == 'transport.events':
            self._handle_event_update(data)
    
    def _handle_telemetry_update(self, telemetry_data):
        """Handle telemetry update and broadcast position changes"""
        device_id = telemetry_data.get('deviceId')
        if not device_id:
            return
        
        # Update vehicle position
        position_data = {
            'deviceId': device_id,
            'timestamp': telemetry_data.get('timestamp'),
            'location': telemetry_data.get('location', {}),
            'speed': telemetry_data.get('speedKmph', 0),
            'heading': telemetry_data.get('heading', 0),
            'status': 'active'
        }
        
        self.vehicle_positions[device_id] = position_data
        
        # Broadcast to vehicle tracking subscribers
        for room_name in self.room_subscriptions:
            if room_name.startswith('vehicle_tracking_'):
                self.socketio.emit('vehicle_position_update', position_data, room=room_name)
    
    def _handle_event_update(self, event_data):
        """Handle event update and broadcast to event subscribers"""
        event = {
            'id': f"event_{int(time.time() * 1000)}",
            'deviceId': event_data.get('deviceId'),
            'type': event_data.get('eventType', 'unknown'),
            'timestamp': event_data.get('timestamp'),
            'location': event_data.get('location', {}),
            'severity': event_data.get('severity', 'low'),
            'data': event_data
        }
        
        # Add to recent events
        self.recent_events.append(event)
        
        # Broadcast to event subscribers
        for room_name in self.room_subscriptions:
            if room_name.startswith('events_'):
                self.socketio.emit('new_event', event, room=room_name)
    
    def _update_live_metrics(self):
        """Update live metrics and broadcast to subscribers"""
        try:
            # Calculate metrics
            active_vehicles = len([v for v in self.vehicle_positions.values() 
                                 if self._is_recent_timestamp(v.get('timestamp'))])
            
            recent_events_count = len([e for e in self.recent_events 
                                     if self._is_recent_timestamp(e.get('timestamp'), minutes=5)])
            
            connected_clients_count = len(self.connected_clients)
            
            self.live_metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'active_vehicles': active_vehicles,
                'recent_events': recent_events_count,
                'connected_clients': connected_clients_count,
                'total_events': len(self.recent_events)
            }
            
            # Broadcast to metrics subscribers
            for room_name in self.room_subscriptions:
                if room_name.startswith('metrics_'):
                    self.socketio.emit('metrics_update', self.live_metrics, room=room_name)
                    
        except Exception as e:
            logger.error(f"Metrics update error: {e}")
    
    def _is_recent_timestamp(self, timestamp_str: str, minutes: int = 2) -> bool:
        """Check if timestamp is recent"""
        if not timestamp_str:
            return False
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=timestamp.tzinfo)
            return (now - timestamp).total_seconds() < (minutes * 60)
        except Exception:
            return False
    
    def broadcast_toll_event(self, toll_data: Dict[str, Any]):
        """Broadcast toll event to all connected clients"""
        event = {
            'id': f"toll_{int(time.time() * 1000)}",
            'type': 'toll_charge',
            'deviceId': toll_data.get('device_id'),
            'gantryId': toll_data.get('gantry_id'),
            'amount': toll_data.get('amount'),
            'timestamp': toll_data.get('timestamp'),
            'txHash': toll_data.get('tx_hash'),
            'paid': toll_data.get('paid', False)
        }
        
        self.recent_events.append(event)
        
        # Broadcast to all event subscribers
        for room_name in self.room_subscriptions:
            if room_name.startswith('events_'):
                self.socketio.emit('toll_event', event, room=room_name)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            'connected_clients': len(self.connected_clients),
            'active_subscriptions': sum(len(subs) for subs in self.room_subscriptions.values()),
            'active_vehicles': len(self.vehicle_positions),
            'recent_events': len(self.recent_events),
            'clients_by_role': {
                role: len([c for c in self.connected_clients.values() if c['role'] == role])
                for role in ['admin', 'operator', 'viewer']
            }
        }

# Global WebSocket manager instance
websocket_manager = None

def init_websocket(app: Flask, redis_client=None, db_config=None) -> WebSocketManager:
    """Initialize WebSocket manager"""
    global websocket_manager
    websocket_manager = WebSocketManager(app, redis_client, db_config)
    return websocket_manager