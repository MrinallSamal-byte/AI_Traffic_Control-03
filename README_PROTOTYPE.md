# Smart Transportation System - Full System Guide

## Architecture Overview

The Smart Transportation System consists of the following components:

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Device        │───▶│ MQTT Broker  │───▶│ Stream Process  │
│   Simulator     │    │   (Port 1883)│    │   (Port 5004)   │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                                     │
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Blockchain    │◀───│  API Server  │◀───│   Database      │
│   (Port 5002)   │    │  (Port 5000) │    │ (PostgreSQL)    │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   ML Services   │
                       │   (Port 5002)   │
                       └─────────────────┘
```

## Quick Start

### Prerequisites

1. **Python 3.8+** with pip
2. **Node.js 14+** with npm
3. **PostgreSQL 12+**
4. **Redis 6+**
5. **Mosquitto MQTT Broker**

### 1. Environment Setup

```bash
# Clone and setup
git clone <repository>
cd Protopype

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Database Setup

```bash
# Start PostgreSQL and create database
createdb transport_system

# Run database migrations
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://admin:password@localhost:5432/transport_system')
cursor = conn.cursor()
cursor.execute(open('database/init.sql').read())
conn.commit()
"
```

### 3. Start Core Services

#### Terminal 1: MQTT Broker
```bash
mosquitto -c config/mosquitto.conf
```

#### Terminal 2: Stream Processor
```bash
cd stream_processor
python processor.py
```

#### Terminal 3: API Server
```bash
cd api_server
python app.py
```

#### Terminal 4: ML Services
```bash
cd ml_services
python serve.py
```

#### Terminal 5: Blockchain Service
```bash
cd blockchain
python blockchain_service.py
```

### 4. Train ML Model

```bash
cd ml/training
python train_harsh_driving.py
```

### 5. Start Dashboard

```bash
# Open dashboard in browser
open dashboard/realtime_dashboard.html
# Or use the enhanced dashboard
open dashboard/index.html
```

### 6. Generate Sample Data

```bash
cd device_simulator
python simulator.py
```

## Component Details

### 1. Telemetry Ingestion & Validation

**Schema**: `stream_processor/schema/telemetry.json`
- Required fields: `deviceId`, `timestamp`, `location`, `speedKmph`, `acceleration`, `fuelLevel`
- Validation using Pydantic models in `stream_processor/schemas.py`
- Invalid messages sent to dead letter queue (`transport.dlq`)

**Testing**:
```bash
python -m pytest tests/unit/test_telemetry_validation.py -v
```

### 2. ML Pipeline

**Training**:
```bash
cd ml/training
python train_harsh_driving.py
```

**Serving API**:
- Endpoint: `POST http://localhost:5002/predict/driver_score`
- Endpoint: `POST http://localhost:5002/predict/harsh_driving`
- Models stored in `ml/models/` with versioning

**Testing**:
```bash
python -m pytest tests/unit/test_ml_inference.py -v
```

### 3. API Security

**Authentication**:
- JWT tokens required for protected endpoints
- Login: `POST /auth/login`
- Rate limiting: 100 requests/minute per IP

**Protected Endpoints**:
- `POST /telemetry/ingest` - Telemetry data ingestion
- `POST /toll/charge` - Toll charging
- `POST /driver_score` - Driver scoring

**Example Usage**:
```bash
# Login
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Use token
curl -X POST http://localhost:5000/telemetry/ingest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"deviceId": "DEVICE_001", ...}'
```

### 4. Real-time Dashboard

**Features**:
- Live telemetry streaming via Server-Sent Events
- Real-time vehicle tracking on map
- Event notifications (harsh driving, speed violations, low fuel)
- System metrics and status

**Access**: `http://localhost:3000` or open `dashboard/realtime_dashboard.html`

### 5. Blockchain Integration

**Smart Contract**: `blockchain/contracts/TollManager.sol`

**API Endpoints**:
- `POST /toll/create` - Create toll record
- `POST /toll/autopay` - Auto-pay toll
- `GET /toll/<id>` - Get toll record
- `GET /balance/<address>` - Get vehicle balance

**Testing**:
```bash
python -m pytest tests/unit/test_blockchain_integration.py -v
```

### 6. Monitoring

**Prometheus Metrics**:
- API Server: `http://localhost:5000/metrics`
- ML Services: `http://localhost:5002/metrics`

**Key Metrics**:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `telemetry_messages_total` - Telemetry ingestion count
- `ml_predictions_total` - ML prediction count
- `toll_transactions_total` - Toll transaction count

**Grafana Dashboard**: Import `ops/grafana_dashboards/transport_system_dashboard.json`

## Sample Data Generation

### Generate Telemetry Data

```bash
cd device_simulator
python simulator.py --devices 10 --duration 300
```

### Sample Telemetry Message

```json
{
  "deviceId": "DEVICE_12345678",
  "timestamp": "2024-01-15T10:30:00Z",
  "location": {
    "lat": 20.2961,
    "lon": 85.8245,
    "altitude": 100.5
  },
  "speedKmph": 65.5,
  "acceleration": {
    "x": 2.1,
    "y": -1.5,
    "z": 9.8
  },
  "fuelLevel": 75.5,
  "heading": 180.0,
  "engineData": {
    "rpm": 2500.0,
    "engineTemp": 85.0
  }
}
```

## Testing

### Run All Tests

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Specific component tests
python -m pytest tests/unit/test_telemetry_validation.py -v
python -m pytest tests/unit/test_ml_inference.py -v
python -m pytest tests/unit/test_blockchain_integration.py -v
```

### Manual Testing

1. **Telemetry Validation**:
```bash
curl -X POST http://localhost:5000/telemetry/ingest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d @tests/data/valid_telemetry.json
```

2. **ML Prediction**:
```bash
curl -X POST http://localhost:5002/predict/driver_score \
  -H "Content-Type: application/json" \
  -d '{"deviceId": "TEST", "speed": 60, "accel_x": 2, "accel_y": 1, "accel_z": 9.8, "jerk": 0.5, "yaw": 0}'
```

3. **Toll Payment**:
```bash
curl -X POST http://localhost:5000/toll/charge \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "DEVICE_001", "gantry_id": 1, "location": {"lat": 20.2961, "lon": 85.8245}, "timestamp": "2024-01-15T10:30:00Z"}'
```

## Production Deployment

### Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Scale specific services
docker-compose up -d --scale api_server=3
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f infra/k8s/
```

### Environment Variables

Key environment variables for production:

```bash
# Security
JWT_SECRET_KEY=<long-random-string>
ADMIN_PASSWORD=<secure-password>
ENCRYPTION_KEY=<32-char-encryption-key>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379

# Blockchain
BLOCKCHAIN_RPC_URL=https://mainnet.infura.io/v3/<key>
BLOCKCHAIN_PRIVATE_KEY=<private-key>

# External APIs
WEATHER_API_KEY=<api-key>
MAPS_API_KEY=<api-key>
```

## Troubleshooting

### Common Issues

1. **MQTT Connection Failed**:
   - Check Mosquitto is running: `systemctl status mosquitto`
   - Verify port 1883 is open: `netstat -an | grep 1883`

2. **Database Connection Error**:
   - Check PostgreSQL status: `systemctl status postgresql`
   - Verify credentials in `.env`

3. **ML Model Not Found**:
   - Train model first: `cd ml/training && python train_harsh_driving.py`
   - Check model path: `ls ml/models/`

4. **Blockchain Connection Failed**:
   - Start Ganache CLI: `ganache-cli`
   - Check RPC URL in `.env`

### Logs

```bash
# API Server logs
tail -f api_server.log

# Stream Processor logs
tail -f stream_processor.log

# ML Services logs
tail -f ml_services.log
```

## Performance Tuning

### Recommended Settings

- **API Server**: 4 workers, 1GB RAM per worker
- **ML Services**: 2 workers, 2GB RAM per worker
- **Stream Processor**: 8GB RAM, SSD storage
- **Database**: Connection pool size 20, shared_buffers 256MB

### Scaling

- **Horizontal**: Use load balancer for API servers
- **Vertical**: Increase RAM for ML services
- **Database**: Use read replicas for analytics queries

## API Reference

### Authentication

```bash
POST /auth/login
{
  "username": "admin",
  "password": "password"
}
```

### Telemetry

```bash
POST /telemetry/ingest
Authorization: Bearer <token>
{
  "deviceId": "DEVICE_001",
  "timestamp": "2024-01-15T10:30:00Z",
  "location": {"lat": 20.2961, "lon": 85.8245},
  "speedKmph": 65.5,
  "acceleration": {"x": 2.1, "y": -1.5, "z": 9.8},
  "fuelLevel": 75.5
}
```

### ML Predictions

```bash
POST /predict/driver_score
{
  "deviceId": "DEVICE_001",
  "speed": 60,
  "accel_x": 2,
  "accel_y": 1,
  "accel_z": 9.8,
  "jerk": 0.5,
  "yaw": 0
}
```

### Monitoring

```bash
GET /health          # Health check
GET /metrics         # Prometheus metrics
GET /metrics/json    # JSON metrics
```

## Support

For issues and questions:
1. Check logs for error messages
2. Verify all services are running
3. Test with sample data
4. Check network connectivity between services