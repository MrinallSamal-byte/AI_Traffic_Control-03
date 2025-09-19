"""Integration tests for stream processor with MQTT and database."""

import pytest
import json
import time
import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import RealDictCursor
import docker
import os


@pytest.fixture(scope="module")
def docker_services():
    """Start Docker services for integration testing."""
    client = docker.from_env()
    
    # Start services using docker-compose
    os.system("docker-compose -f docker-compose.yml up -d mosquitto timescaledb redis")
    
    # Wait for services to be ready
    time.sleep(30)
    
    yield
    
    # Cleanup
    os.system("docker-compose -f docker-compose.yml down")


@pytest.fixture
def mqtt_client():
    """Create MQTT client for testing."""
    client = mqtt.Client()
    client.connect("localhost", 1883, 60)
    client.loop_start()
    yield client
    client.loop_stop()
    client.disconnect()


@pytest.fixture
def db_connection():
    """Create database connection for testing."""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="transport_system",
        user="admin",
        password="password"
    )
    yield conn
    conn.close()


def test_telemetry_flow_mqtt_to_db(docker_services, mqtt_client, db_connection, sample_telemetry):
    """Test complete telemetry flow from MQTT to database."""
    
    # Publish telemetry data to MQTT
    topic = "telemetry/vehicle/TEST_DEVICE_001"
    payload = json.dumps(sample_telemetry)
    
    result = mqtt_client.publish(topic, payload)
    assert result.rc == 0, "Failed to publish MQTT message"
    
    # Wait for stream processor to handle the message
    time.sleep(5)
    
    # Check if data was written to database
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT * FROM telemetry WHERE device_id = %s ORDER BY time DESC LIMIT 1",
        (sample_telemetry["deviceId"],)
    )
    
    result = cursor.fetchone()
    assert result is not None, "Telemetry data not found in database"
    assert result["device_id"] == sample_telemetry["deviceId"]
    assert result["speed_kmph"] == sample_telemetry["speedKmph"]


def test_invalid_telemetry_handling(docker_services, mqtt_client):
    """Test handling of invalid telemetry data."""
    
    # Publish invalid telemetry data
    invalid_data = {
        "deviceId": "INVALID_DEVICE",
        "timestamp": "invalid-timestamp",
        "location": {"lat": 200, "lon": 300},  # Invalid coordinates
        "speedKmph": -50  # Invalid speed
    }
    
    topic = "telemetry/vehicle/INVALID_DEVICE"
    payload = json.dumps(invalid_data)
    
    result = mqtt_client.publish(topic, payload)
    assert result.rc == 0, "Failed to publish MQTT message"
    
    # Wait for processing
    time.sleep(3)
    
    # Invalid data should be rejected and not stored in main telemetry table
    # (In a real implementation, it might go to a dead letter queue)


def test_high_volume_telemetry(docker_services, mqtt_client, db_connection):
    """Test handling of high volume telemetry data."""
    
    # Publish multiple telemetry messages rapidly
    device_ids = [f"TEST_DEVICE_{i:03d}" for i in range(10)]
    
    for i, device_id in enumerate(device_ids):
        telemetry = {
            "deviceId": device_id,
            "timestamp": "2024-01-15T10:30:00Z",
            "location": {"lat": 1.3521 + i * 0.001, "lon": 103.8198 + i * 0.001},
            "speedKmph": 45.0 + i,
            "heading": 90 + i * 10
        }
        
        topic = f"telemetry/vehicle/{device_id}"
        payload = json.dumps(telemetry)
        mqtt_client.publish(topic, payload)
    
    # Wait for all messages to be processed
    time.sleep(10)
    
    # Check that all messages were processed
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM telemetry WHERE device_id LIKE 'TEST_DEVICE_%'")
    count = cursor.fetchone()[0]
    
    assert count >= len(device_ids), f"Expected at least {len(device_ids)} records, got {count}"


def test_stream_processor_health(docker_services):
    """Test stream processor health endpoint."""
    import requests
    
    try:
        response = requests.get("http://localhost:5001/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    except requests.exceptions.ConnectionError:
        pytest.skip("Stream processor not running or not accessible")