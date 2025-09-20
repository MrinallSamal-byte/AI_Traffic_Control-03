# Smart Transportation System - Prototype Guide

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.8+
- Node.js 16+ (for frontend)

### 1. Start Infrastructure Services
```bash
# Start all infrastructure services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Start Application Services

#### Terminal 1: Stream Processor
```bash
cd stream_processor
python processor.py
```

#### Terminal 2: ML Services
```bash
cd ml_services
python serve.py
```

#### Terminal 3: Blockchain Service
```bash
cd blockchain
python blockchain_service.py
```

#### Terminal 4: API Server
```bash
cd api_server
python app.py
```

### 3. Train ML Model (First Time)
```bash
cd ml/training
python train_enhanced.py --samples 10000
```

### 4. Generate Demo Data
```bash
cd tools
python demo_data_generator.py --vehicles 5 --duration 10
```

## System Architecture Flow

```
Device Simulator → MQTT → Stream Processor → Kafka → Database
                                    ↓
                            ML Services ← API Server → WebSocket → Dashboard
                                    ↓
                            Blockchain Service
```

## Step-by-Step Verification

### 1. Health Checks
```bash
# Check all services are healthy
curl http://localhost:5000/health  # API Server
curl http://localhost:5002/health  # ML Services
curl http://localhost:5004/health  # Stream Processor
curl http://localhost:5002/health  # Blockchain Service
```

### 2. Authentication
```bash
# Login to get JWT token
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Save the access_token from response
export TOKEN="your_access_token_here"
```

### 3. Telemetry Ingestion
```bash
# Send valid telemetry
curl -X POST http://localhost:5000/telemetry/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "TEST_001",
    "timestamp": "2024-01-15T10:30:00Z",
    "location": {"lat": 20.2961, "lon": 85.8245},
    "speedKmph": 45.5,
    "acceleration": {"x": 1.2, "y": -0.8, "z": 9.8},
    "fuelLevel": 75.5
  }'
```

### 4. ML Prediction
```bash
# Get driver score prediction
curl -X POST http://localhost:5002/predict \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "TEST_001",
    "speed": 45.5,
    "accel_x": 1.2,
    "accel_y": -0.8,
    "accel_z": 9.8,
    "jerk": 0.5,
    "yaw": 2.0
  }'
```

Expected output:
```json
{
  "deviceId": "TEST_001",
  "prediction": 25.4,
  "model_version": "random_forest_v1",
  "confidence": 0.85,
  "timestamp": "2024-01-15T10:30:00Z",
  "processing_time_ms": 12.5
}
```

### 5. Toll Event
```bash
# Trigger toll charge
curl -X POST http://localhost:5000/toll/charge \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST_001",
    "gantry_id": "GANTRY_001",
    "location": {"lat": 20.3000, "lon": 85.8300},
    "timestamp": "2024-01-15T10:30:00Z"
  }'
```

Expected output:
```json
{
  "device_id": "TEST_001",
  "gantry_id": "GANTRY_001",
  "amount": 0.05,
  "toll_id": 1,
  "tx_hash": "0x...",
  "paid": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 6. Real-time Dashboard
1. Open browser: http://localhost:3000/realtime_enhanced.html
2. Login with admin/admin123
3. Observe live vehicle positions and events

### 7. Monitoring
```bash
# View Prometheus metrics
curl http://localhost:5000/metrics
curl http://localhost:5002/metrics
curl http://localhost:5004/metrics

# View JSON metrics
curl http://localhost:5000/metrics/json
```

## Demo Scenarios

### Scenario 1: Normal Operation
```bash
# Generate normal traffic
python tools/demo_data_generator.py --vehicles 3 --duration 5
```
- Vehicles move normally
- Occasional events generated
- All telemetry validated and processed

### Scenario 2: Harsh Driving Events
```bash
# Generate aggressive driving patterns
python tools/demo_data_generator.py --vehicles 2 --duration 3
```
- Watch for HARSH_BRAKE and HARSH_ACCEL events
- ML model detects high-risk behavior
- Events appear in real-time dashboard

### Scenario 3: Invalid Data Handling
```bash
# Demo includes ~2% invalid messages
python tools/demo_data_generator.py --vehicles 1 --duration 2
```
- Invalid messages sent to dead letter queue
- Valid messages processed normally
- Check DLQ metrics in monitoring

### Scenario 4: Toll Processing
```bash
# Vehicles cross toll gantries
python tools/demo_data_generator.py --vehicles 2 --duration 10
```
- Automatic toll detection when near gantries
- Blockchain transactions recorded
- Payment status tracked

## Expected Outputs

### ML Predictions
- **Low Risk**: prediction < 30 (normal driving)
- **Medium Risk**: 30 ≤ prediction < 70 (moderate events)
- **High Risk**: prediction ≥ 70 (harsh driving detected)

### Toll Transactions
- **Successful**: `paid: true`, transaction hash present
- **Failed**: `paid: false`, insufficient balance or contract error

### Event Types
- `HARSH_BRAKE`: Sudden deceleration detected
- `HARSH_ACCEL`: Rapid acceleration detected
- `SPEED_VIOLATION`: Speed limit exceeded
- `toll_charge`: Vehicle crossed toll gantry

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check Docker services
   docker-compose logs
   
   # Check ports
   netstat -tulpn | grep -E ':(5000|5002|5004|1883|9092|5432|6379|8545)'
   ```

2. **Authentication failures**
   ```bash
   # Verify credentials
   curl -X POST http://localhost:5000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
   ```

3. **ML model not found**
   ```bash
   # Train model first
   cd ml/training
   python train_enhanced.py
   ```

4. **Blockchain connection issues**
   ```bash
   # Check Ganache is running
   curl -X POST http://localhost:8545 \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_accounts","params":[],"id":1}'
   ```

### Log Locations
- API Server: Console output
- Stream Processor: Console output + port 5004/health
- ML Services: Console output + port 5002/health
- Blockchain: Console output + port 5002/health

### Performance Expectations
- **Telemetry Processing**: 100+ messages/second
- **ML Predictions**: <100ms response time
- **Toll Transactions**: <2 seconds end-to-end
- **WebSocket Updates**: <500ms latency

## Development

### Adding New Features
1. Update relevant service
2. Add unit tests
3. Update monitoring metrics
4. Test with demo data generator

### Configuration
- Environment variables in `.env` files
- Service configs in respective directories
- Docker Compose overrides in `docker-compose.override.yml`

### Testing
```bash
# Run all tests
make test

# Run specific component tests
pytest tests/unit/test_telemetry_validation_enhanced.py
pytest tests/unit/test_ml_serving_enhanced.py
pytest tests/unit/test_blockchain_integration_enhanced.py
```

## Production Considerations

### Security
- Change default passwords
- Use proper JWT secrets
- Enable HTTPS/TLS
- Implement proper RBAC

### Scalability
- Use Kafka partitioning
- Scale ML services horizontally
- Implement database sharding
- Use load balancers

### Monitoring
- Set up Prometheus + Grafana
- Configure alerting rules
- Monitor resource usage
- Track business metrics