#!/usr/bin/env python3
"""
Telemetry Replay Tool - Replay stored telemetry at variable speeds
"""

import json
import time
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta

class TelemetryReplay:
    def __init__(self, db_config, mqtt_config):
        self.db_config = db_config
        self.mqtt_config = mqtt_config
        self.mqtt_client = mqtt.Client()
        
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        self.mqtt_client.connect(self.mqtt_config['host'], self.mqtt_config['port'], 60)
        self.mqtt_client.loop_start()
        
    def get_telemetry_data(self, device_id=None, start_time=None, end_time=None, limit=1000):
        """Fetch telemetry data from database"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM telemetry WHERE 1=1"
        params = []
        
        if device_id:
            query += " AND device_id = %s"
            params.append(device_id)
            
        if start_time:
            query += " AND time >= %s"
            params.append(start_time)
            
        if end_time:
            query += " AND time <= %s"
            params.append(end_time)
            
        query += " ORDER BY time ASC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [dict(row) for row in data]
    
    def replay_telemetry(self, data, speed_multiplier=1.0):
        """Replay telemetry data at specified speed"""
        if not data:
            print("No data to replay")
            return
            
        print(f"Replaying {len(data)} telemetry records at {speed_multiplier}x speed")
        
        start_time = None
        for i, record in enumerate(data):
            current_time = record['time']
            
            if start_time is None:
                start_time = current_time
                last_time = current_time
            else:
                # Calculate delay based on original timing
                time_diff = (current_time - last_time).total_seconds()
                adjusted_delay = time_diff / speed_multiplier
                
                if adjusted_delay > 0:
                    time.sleep(adjusted_delay)
                
                last_time = current_time
            
            # Convert to telemetry format
            telemetry = {
                "deviceId": record['device_id'],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "location": {
                    "lat": float(record['latitude']),
                    "lon": float(record['longitude'])
                },
                "speedKmph": float(record['speed_kmph']),
                "heading": float(record['heading']),
                "imu": {
                    "ax": float(record['acceleration_x']),
                    "ay": float(record['acceleration_y']),
                    "az": float(record['acceleration_z'])
                },
                "can": {
                    "rpm": int(record['rpm']),
                    "throttle": float(record['throttle']),
                    "brake": float(record['brake'])
                },
                "batteryVoltage": float(record['battery_voltage'])
            }
            
            # Publish to MQTT
            topic = f"/org/demo/device/{record['device_id']}/telemetry"
            self.mqtt_client.publish(topic, json.dumps(telemetry))
            
            if (i + 1) % 100 == 0:
                print(f"Replayed {i + 1}/{len(data)} records")
        
        print("Replay completed")

def main():
    parser = argparse.ArgumentParser(description="Telemetry Replay Tool")
    parser.add_argument("--device-id", help="Specific device ID to replay")
    parser.add_argument("--speed", type=float, default=1.0, help="Replay speed multiplier")
    parser.add_argument("--hours", type=int, default=1, help="Hours of data to replay")
    parser.add_argument("--limit", type=int, default=1000, help="Max records to replay")
    
    args = parser.parse_args()
    
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'transport_system',
        'user': 'admin',
        'password': 'password'
    }
    
    mqtt_config = {
        'host': 'localhost',
        'port': 1883
    }
    
    replay = TelemetryReplay(db_config, mqtt_config)
    replay.connect_mqtt()
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=args.hours)
    
    # Get data and replay
    data = replay.get_telemetry_data(
        device_id=args.device_id,
        start_time=start_time,
        end_time=end_time,
        limit=args.limit
    )
    
    replay.replay_telemetry(data, args.speed)

if __name__ == "__main__":
    main()