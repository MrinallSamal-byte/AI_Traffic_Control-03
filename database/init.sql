-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vehicles table
CREATE TABLE vehicles (
    vehicle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    registration_no VARCHAR(20) UNIQUE NOT NULL,
    obu_device_id VARCHAR(50) UNIQUE,
    wallet_address VARCHAR(42),
    ais140_compliant BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Wallets table
CREATE TABLE wallets (
    wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID REFERENCES vehicles(vehicle_id),
    balance DECIMAL(10,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'ETH',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Toll gantries table
CREATE TABLE toll_gantries (
    gantry_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    geo_polygon TEXT,
    lane_count INTEGER DEFAULT 1,
    base_price DECIMAL(8,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Toll transactions table
CREATE TABLE toll_transactions (
    tx_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID REFERENCES vehicles(vehicle_id),
    gantry_id VARCHAR(20) REFERENCES toll_gantries(gantry_id),
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    price DECIMAL(8,2) NOT NULL,
    smart_contract_tx_hash VARCHAR(66),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Telemetry table (TimescaleDB hypertable)
CREATE TABLE telemetry (
    time TIMESTAMP NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    speed_kmph DECIMAL(5,2),
    heading DECIMAL(5,2),
    acceleration_x DECIMAL(6,3),
    acceleration_y DECIMAL(6,3),
    acceleration_z DECIMAL(6,3),
    gyro_x DECIMAL(6,3),
    gyro_y DECIMAL(6,3),
    gyro_z DECIMAL(6,3),
    rpm INTEGER,
    throttle DECIMAL(5,2),
    brake DECIMAL(5,2),
    battery_voltage DECIMAL(4,2),
    signature TEXT
);

-- Convert to hypertable
SELECT create_hypertable('telemetry', 'time');

-- Driver scores table
CREATE TABLE driver_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID REFERENCES vehicles(vehicle_id),
    timestamp TIMESTAMP NOT NULL,
    score INTEGER CHECK (score >= 0 AND score <= 100),
    features_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events table
CREATE TABLE events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    speed_before DECIMAL(5,2),
    speed_after DECIMAL(5,2),
    accel_peak DECIMAL(6,3),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_telemetry_device_time ON telemetry (device_id, time DESC);
CREATE INDEX idx_events_device_time ON events (device_id, timestamp DESC);
CREATE INDEX idx_toll_transactions_vehicle ON toll_transactions (vehicle_id, created_at DESC);

-- Sample data
INSERT INTO users (name, email, phone) VALUES 
('John Doe', 'john@example.com', '+1234567890'),
('Jane Smith', 'jane@example.com', '+1234567891');

INSERT INTO vehicles (user_id, registration_no, obu_device_id, wallet_address) VALUES 
((SELECT user_id FROM users WHERE email = 'john@example.com'), 'ABC123', 'OBU-001', '0x742d35Cc6634C0532925a3b8D4C2C4e07C3c4526'),
((SELECT user_id FROM users WHERE email = 'jane@example.com'), 'XYZ789', 'OBU-002', '0x8ba1f109551bD432803012645Hac136c9c3c4527');

INSERT INTO wallets (vehicle_id, balance) VALUES 
((SELECT vehicle_id FROM vehicles WHERE registration_no = 'ABC123'), 100.00),
((SELECT vehicle_id FROM vehicles WHERE registration_no = 'XYZ789'), 150.00);

INSERT INTO toll_gantries (gantry_id, name, latitude, longitude, base_price) VALUES 
('G-001', 'Highway Entry Point 1', 20.2961, 85.8245, 25.00),
('G-002', 'City Center Toll', 20.3000, 85.8300, 15.00),
('G-003', 'Airport Express', 20.2500, 85.8100, 50.00);