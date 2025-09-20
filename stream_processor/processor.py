#!/usr/bin/env python3
"""
Stream Processor - MQTT to Kafka to Database Pipeline
Handles real-time telemetry validation, enrichment, and routing
"""

import json
import time
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
from kafka import KafkaProducer, KafkaConsumer
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import logging
from collections import defaultdict, deque
from pydantic import ValidationError
from schemas import TelemetryModel, EventModel, V2XModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamProcessor:
    def __init__(self, config):
        self.config = config
        self.mqtt_client = mqtt.Client()
        self.kafka_producer = None
        self.redis_client = None
        self.db_conn = None
        
        # Rate limiting
        self.device_message_counts = defaultdict(lambda: deque(maxlen=100))
        self.rate_limit_threshold = config.get('rate_limit', {}).get('messages_per_minute', 60)
        
        # Static road data for enrichment
        self.road_segments = self._load_road_segments()
        
        # Setup MQTT callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        self._setup_connections()
    
    def _setup_connections(self):
        """Initialize all connections"""
        try:
            # Kafka Producer
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.config['kafka']['servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            
            # Redis
            self.redis_client = redis.Redis(
                host=self.config['redis']['host'],
                port=self.config['redis']['port'],
                decode_responses=True
            )
            
            # PostgreSQL
            self.db_conn = psycopg2.connect(
                host=self.config['postgres']['host'],
                port=self.config['postgres']['port'],
                database=self.config['postgres']['database'],
                user=self.config['postgres']['user'],
                password=self.config['postgres']['password']
            )
            
            logger.info("✓ All connections established")
            
        except Exception as e:
            logger.error(f"✗ Connection setup failed: {e}")
            raise
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✓ Connected to MQTT broker")
            # Subscribe to all telemetry and events
            client.subscribe("/org/+/device/+/telemetry")
            client.subscribe("/org/+/device/+/events")
            client.subscribe("/org/+/device/+/v2x")
        else:
            logger.error(f"✗ MQTT connection failed: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Process incoming MQTT messages"""
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) < 5:
                return
            
            org_id = topic_parts[2]
            device_id = topic_parts[4]
            message_type = topic_parts[5]
            
            # Rate limiting check
            if not self._check_rate_limit(device_id):
                logger.warning(f"Rate limit exceeded for device {device_id}")
                return
            
            try:
                payload = json.loads(msg.payload.decode())
            except json.JSONDecodeError as e:
                # Send to dead letter queue
                self._send_to_dlq(msg.payload, f"Invalid JSON: {e}", device_id)
                return
            
            # Validate and enrich message
            enriched_payload = self._validate_and_enrich(payload, message_type, device_id)
            
            if enriched_payload:
                # Route to appropriate Kafka topic
                kafka_topic = f"transport.{message_type}"
                self.kafka_producer.send(
                    kafka_topic,
                    key=device_id,
                    value=enriched_payload
                )
                
                logger.info(f"📨 Processed {message_type} from {device_id}")
            else:
                # Send invalid message to DLQ
                self._send_to_dlq(payload, "Validation failed", device_id)
            
        except Exception as e:
            logger.error(f"✗ Message processing error: {e}")
            self._send_to_dlq(msg.payload, f"Processing error: {e}", device_id)
    
    def _validate_and_enrich(self, payload, message_type, device_id):
        """Validate message using Pydantic models and add enrichment data"""
        try:
            # Basic validation
            if not payload.get('timestamp'):
                payload['timestamp'] = datetime.utcnow().isoformat() + 'Z'
            
            if not payload.get('deviceId'):
                payload['deviceId'] = device_id
            
            # Message type specific validation using Pydantic
            if message_type == 'telemetry':
                try:
                    validated = TelemetryModel(**payload)
                    return self._enrich_telemetry(validated.dict())
                except ValidationError as e:
                    logger.warning(f"Telemetry validation failed: {e}")
                    return None
            elif message_type == 'events':
                try:
                    validated = EventModel(**payload)
                    return self._enrich_event(validated.dict())
                except ValidationError as e:
                    logger.warning(f"Event validation failed: {e}")
                    return None
            elif message_type == 'v2x':
                try:
                    validated = V2XModel(**payload)
                    return self._enrich_v2x(validated.dict())
                except ValidationError as e:
                    logger.warning(f"V2X validation failed: {e}")
                    return None
            
            return payload
            
        except Exception as e:
            logger.error(f"✗ Validation error: {e}")
            return None
    
    def _enrich_telemetry(self, payload):
        """Enrich validated telemetry message"""
        location = payload['location']
        
        # Add enrichment
        payload['processed_at'] = datetime.utcnow().isoformat() + 'Z'
        road_info = self._enrich_with_road_data(location['lat'], location['lon'])
        payload['road_segment_id'] = road_info['segment_id']
        payload['speed_limit'] = road_info['speed_limit']
        payload['road_type'] = road_info['road_type']
        
        # Cache latest position for geofencing
        self.redis_client.setex(
            f"position:{payload['deviceId']}",
            300,  # 5 minutes TTL
            json.dumps({
                'lat': location['lat'],
                'lon': location['lon'],
                'timestamp': payload['timestamp']
            })
        )
        
        return payload
    
    def _enrich_event(self, payload):
        """Enrich validated event message"""
        # Add enrichment
        payload['processed_at'] = datetime.utcnow().isoformat() + 'Z'
        payload['severity'] = self._calculate_event_severity(payload)
        
        return payload
    
    def _enrich_v2x(self, payload):
        """Enrich validated V2X message"""
        # Add enrichment
        payload['processed_at'] = datetime.utcnow().isoformat() + 'Z'
        payload['ttl_expires_at'] = datetime.utcnow().timestamp() + payload.get('ttl_seconds', 5)
        
        return payload
    
    def _load_road_segments(self):
        """Load static road segment data"""
        # Mock road segments - in production load from database/file
        return {
            'default': {'speed_limit': 50, 'road_type': 'urban'},
            'highway': {'speed_limit': 100, 'road_type': 'highway'},
            'residential': {'speed_limit': 30, 'road_type': 'residential'}
        }
    
    def _check_rate_limit(self, device_id):
        """Check if device is within rate limits"""
        now = time.time()
        device_times = self.device_message_counts[device_id]
        
        # Remove old timestamps (older than 1 minute)
        while device_times and device_times[0] < now - 60:
            device_times.popleft()
        
        # Check if under limit
        if len(device_times) >= self.rate_limit_threshold:
            return False
        
        # Add current timestamp
        device_times.append(now)
        return True
    
    def _send_to_dlq(self, payload, error_reason, device_id):
        """Send invalid messages to dead letter queue"""
        dlq_message = {
            'original_payload': payload.decode() if isinstance(payload, bytes) else payload,
            'error_reason': error_reason,
            'device_id': device_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        try:
            self.kafka_producer.send(
                'transport.dlq',
                key=device_id,
                value=dlq_message
            )
            logger.warning(f"Sent message to DLQ: {error_reason}")
        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")
    
    def _enrich_with_road_data(self, lat, lon):
        """Enrich telemetry with road segment information"""
        # Simple road type detection based on coordinates
        # In production, use proper map matching service
        
        segment_id = f"SEG_{int(lat * 1000)}_{int(lon * 1000)}"
        
        # Determine road type based on location patterns
        if abs(lat - 20.2961) < 0.01 and abs(lon - 85.8245) < 0.01:
            road_type = 'urban'
        elif abs(lat - 20.3) < 0.005:
            road_type = 'highway'
        else:
            road_type = 'residential'
        
        road_info = self.road_segments.get(road_type, self.road_segments['default'])
        
        return {
            'segment_id': segment_id,
            'speed_limit': road_info['speed_limit'],
            'road_type': road_info['road_type']
        }
    
    def _calculate_event_severity(self, event):
        """Calculate event severity based on type and parameters"""
        event_type = event.get('eventType', '')
        
        if event_type in ['HARSH_BRAKE', 'HARSH_ACCEL']:
            accel_peak = abs(event.get('accelPeak', 0))
            if accel_peak > 8:
                return 'HIGH'
            elif accel_peak > 6:
                return 'MEDIUM'
            else:
                return 'LOW'
        
        return 'LOW'
    
    def start_kafka_consumers(self):
        """Start Kafka consumers for database persistence"""
        consumers = [
            ('transport.telemetry', self._process_telemetry_batch),
            ('transport.events', self._process_events_batch),
            ('transport.v2x', self._process_v2x_batch),
            ('transport.dlq', self._process_dlq_batch)
        ]
        
        for topic, processor in consumers:
            thread = threading.Thread(
                target=self._kafka_consumer_loop,
                args=(topic, processor)
            )
            thread.daemon = True
            thread.start()
            logger.info(f"✓ Started consumer for {topic}")
    
    def _kafka_consumer_loop(self, topic, processor):
        """Kafka consumer loop"""
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self.config['kafka']['servers'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id=f"stream_processor_{topic}",
            auto_offset_reset='latest'
        )
        
        batch = []
        batch_size = 100
        last_commit = time.time()
        
        for message in consumer:
            batch.append(message.value)
            
            # Process batch when full or after timeout
            if len(batch) >= batch_size or (time.time() - last_commit) > 5:
                try:
                    processor(batch)
                    batch = []
                    last_commit = time.time()
                    consumer.commit()
                except Exception as e:
                    logger.error(f"✗ Batch processing error: {e}")
    
    def _process_telemetry_batch(self, batch):
        """Process telemetry batch to database"""
        if not batch:
            return
        
        cursor = self.db_conn.cursor()
        
        insert_query = """
        INSERT INTO telemetry (
            time, device_id, latitude, longitude, speed_kmph, heading,
            acceleration_x, acceleration_y, acceleration_z,
            gyro_x, gyro_y, gyro_z, rpm, throttle, brake,
            battery_voltage, signature
        ) VALUES %s
        """
        
        values = []
        for item in batch:
            location = item.get('location', {})
            imu = item.get('imu', {})
            can = item.get('can', {})
            
            values.append((
                item.get('timestamp'),
                item.get('deviceId'),
                location.get('lat'),
                location.get('lon'),
                item.get('speedKmph'),
                item.get('heading'),
                imu.get('ax'),
                imu.get('ay'),
                imu.get('az'),
                imu.get('gx'),
                imu.get('gy'),
                imu.get('gz'),
                can.get('rpm'),
                can.get('throttle'),
                can.get('brake'),
                item.get('batteryVoltage'),
                item.get('signature')
            ))
        
        psycopg2.extras.execute_values(cursor, insert_query, values)
        self.db_conn.commit()
        cursor.close()
        
        logger.info(f"💾 Stored {len(batch)} telemetry records")
    
    def _process_events_batch(self, batch):
        """Process events batch to database"""
        if not batch:
            return
        
        cursor = self.db_conn.cursor()
        
        insert_query = """
        INSERT INTO events (
            device_id, event_type, timestamp, latitude, longitude,
            speed_before, speed_after, accel_peak, metadata
        ) VALUES %s
        """
        
        values = []
        for item in batch:
            location = item.get('location', {})
            
            values.append((
                item.get('deviceId'),
                item.get('eventType'),
                item.get('timestamp'),
                location.get('lat'),
                location.get('lon'),
                item.get('speedBefore'),
                item.get('speedAfter'),
                item.get('accelPeak'),
                json.dumps({k: v for k, v in item.items() if k not in [
                    'deviceId', 'eventType', 'timestamp', 'location',
                    'speedBefore', 'speedAfter', 'accelPeak'
                ]})
            ))
        
        psycopg2.extras.execute_values(cursor, insert_query, values)
        self.db_conn.commit()
        cursor.close()
        
        logger.info(f"🚨 Stored {len(batch)} event records")
    
    def _process_v2x_batch(self, batch):
        """Process V2X messages (cache for real-time access)"""
        if not batch:
            return
        
        for item in batch:
            # Store in Redis for real-time V2X message exchange
            key = f"v2x:{item.get('deviceId')}:{item.get('type')}"
            self.redis_client.setex(
                key,
                item.get('ttl_seconds', 5),
                json.dumps(item)
            )
        
        logger.info(f"📡 Cached {len(batch)} V2X messages")
    
    def _process_dlq_batch(self, batch):
        """Process dead letter queue messages for debugging"""
        if not batch:
            return
        
        cursor = self.db_conn.cursor()
        
        insert_query = """
        INSERT INTO dead_letter_queue (
            device_id, error_reason, original_payload, timestamp
        ) VALUES %s
        """
        
        values = []
        for item in batch:
            values.append((
                item.get('device_id'),
                item.get('error_reason'),
                json.dumps(item.get('original_payload')),
                item.get('timestamp')
            ))
        
        psycopg2.extras.execute_values(cursor, insert_query, values)
        self.db_conn.commit()
        cursor.close()
        
        logger.warning(f"🚨 Stored {len(batch)} DLQ messages")
    
    def start(self):
        """Start the stream processor"""
        logger.info("🚀 Starting Stream Processor")
        
        # Start Kafka consumers
        self.start_kafka_consumers()
        
        # Connect to MQTT and start processing
        self.mqtt_client.connect(
            self.config['mqtt']['host'],
            self.config['mqtt']['port'],
            60
        )
        
        self.mqtt_client.loop_forever()

# Health endpoint for stream processor
from flask import Flask
from flask_cors import CORS
import threading

def create_health_server():
    """Create health check server for stream processor"""
    health_app = Flask(__name__)
    CORS(health_app)
    
    @health_app.route('/health', methods=['GET'])
    def health():
        return {
            'status': 'healthy',
            'service': 'stream_processor',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    return health_app

if __name__ == "__main__":
    config = {
        'mqtt': {
            'host': 'localhost',
            'port': 1883
        },
        'kafka': {
            'servers': ['localhost:9092']
        },
        'redis': {
            'host': 'localhost',
            'port': 6379
        },
        'postgres': {
            'host': 'localhost',
            'port': 5432,
            'database': 'transport_system',
            'user': 'admin',
            'password': 'password'
        },
        'rate_limit': {
            'messages_per_minute': 60
        }
    }
    
    processor = StreamProcessor(config)
    
    # Start health server in background
    health_app = create_health_server()
    health_thread = threading.Thread(
        target=lambda: health_app.run(host='0.0.0.0', port=5004, debug=False),
        daemon=True
    )
    health_thread.start()
    logger.info("✓ Health server started on port 5004")
    
    try:
        processor.start()
    except KeyboardInterrupt:
        logger.info("🛑 Stream processor stopped")
    except Exception as e:
        logger.error(f"✗ Stream processor error: {e}")