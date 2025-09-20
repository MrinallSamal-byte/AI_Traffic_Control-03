# Smart Transportation System - Enhanced Production-Ready Prototype

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Vehicle Edge  │───▶│ MQTT Broker  │───▶│ Stream Process  │
│ (OBU/Simulator) │    │  (Enhanced)  │    │  (Validation)   │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                                     │
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Blockchain    │◀───│  API Gateway │◀───│   Data Layer    │
│ (Enhanced Toll) │    │ (Auth+WebSkt)│    │ (Postgres/TS)   │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   ML Services   │
                       │ (Enhanced API)  │
                       └─────────────────┘
```

## 🚀 Quick Start

### One-Command Launch (Recommended)
```bash
# Start the complete system with demo data
python start_enhanced_prototype.py --demo
```

### Manual Setup
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Individual Services**:
   ```bash
   # Core infrastructure
   redis-server --port 6379
   mosquitto -c config/mosquitto.conf
   
   # Application services
   python blockchain/enhanced_blockchain_service.py
   python stream_processor/processor.py
   python ml_services/enhanced_ml_api.py
   python api_server/app.py
   python api_server/websocket_manager.py
   ```

3. **Access Interfaces**:
   - **Real-time Dashboard**: `dashboard/realtime_enhanced_dashboard.html`
   - **API Documentation**: `http://localhost:5002/docs`
   - **System Health**: `http://localhost:5000/health`

## 🎯 Key Features Implemented

### ✅ Telemetry Validation & Flow Control
- **Enhanced JSON Schema**: Comprehensive telemetry validation
- **Dead Letter Queue**: Invalid messages routed to DLQ for analysis
- **Map Matching**: GPS coordinates matched to road segments
- **Data Enrichment**: Speed limits, geofencing, derived metrics
- **Business Rules**: Realistic validation (speed vs acceleration correlation)

### ✅ ML Training & Serving
- **Baseline Model**: RandomForest for harsh driving detection
- **Model Versioning**: Automated model versioning and metadata
- **Enhanced API**: FastAPI with batch predictions, health checks
- **Fallback System**: Heuristic predictions when ML models fail
- **Comprehensive Testing**: Unit tests for all ML components

### ✅ API Security & Device Authentication
- **Multi-Auth Support**: JWT tokens, API keys, certificate-based auth
- **Role-Based Access**: Admin, operator, viewer roles with permissions
- **Rate Limiting**: Per-user/device rate limiting with Redis
- **Security Headers**: CORS, authentication middleware
- **Environment Variables**: All secrets externalized

### ✅ Dashboard Real-Time Streaming
- **WebSocket Integration**: Real-time telemetry, events, predictions
- **Interactive Maps**: Live vehicle tracking with Leaflet
- **Live Charts**: Speed distribution, risk predictions, system metrics
- **Subscription Management**: Filter by device, stream type
- **Authentication**: Secure WebSocket connections with JWT

### ✅ Blockchain Tolling Integration
- **Enhanced Smart Contracts**: Comprehensive toll management
- **Transaction Monitoring**: Real-time transaction status tracking
- **Error Handling**: Retry logic, timeout handling, failure recovery
- **Gas Optimization**: Efficient contract interactions
- **Balance Management**: Vehicle balance deposits and withdrawals

### ✅ Monitoring & Observability
- **Prometheus Metrics**: Comprehensive system metrics collection
- **Grafana Dashboards**: Pre-configured monitoring dashboards
- **Alert Rules**: Critical, warning, and info-level alerts
- **Health Checks**: Service health monitoring and reporting
- **Performance Tracking**: Latency, throughput, error rates

## 🧪 Demo Scenarios

### Automated Demo
```bash
# Run complete demo with multiple vehicles
python start_enhanced_prototype.py --demo

# Generate specific scenarios
python tools/enhanced_demo_data_generator.py --vehicles 10 --scenario aggressive --duration 5
```

### Manual Testing
```bash
# Test ML predictions
curl -X POST http://localhost:5002/predict \
  -H "Content-Type: application/json" \
  -d '{"deviceId":"TEST_001","speed":85,"accel_x":8.5,"accel_y":3.2,"accel_z":9.8}'

# Test toll charging
curl -X POST http://localhost:5000/toll/charge \
  -H "Content-Type: application/json" \
  -d '{"device_id":"TEST_001","gantry_id":"GANTRY_001","location":{"lat":20.2961,"lon":85.8245}}'
```

## 📊 System Components

| Component | Port | Description | Health Check |
|-----------|------|-------------|-------------|
| **API Server** | 5000 | Main REST API with WebSocket | `/health` |
| **WebSocket Manager** | 5001 | Real-time streaming | `/health` |
| **ML Services** | 5002 | Enhanced ML API | `/health`, `/docs` |
| **Blockchain Service** | 5003 | Smart contract interface | `/health` |
| **Stream Processor** | 5004 | Telemetry validation | `/health` |
| **Redis** | 6379 | Cache and rate limiting | - |
| **MQTT Broker** | 1883 | Message broker | - |
| **PostgreSQL** | 5432 | Primary database | - |

## 🔧 Development Commands

```bash
# Run tests
python -m pytest tests/ -v

# Train ML model
python ml/training/train_baseline_harsh_driving.py

# Generate demo data
python tools/enhanced_demo_data_generator.py --vehicles 5 --duration 10

# Check system health
curl http://localhost:5000/health
curl http://localhost:5002/health
curl http://localhost:5003/health

# View metrics
curl http://localhost:5000/metrics
curl http://localhost:5002/metrics
```

## 📈 Monitoring

### Grafana Dashboard
- Import: `ops/grafana_dashboards/comprehensive_transport_dashboard.json`
- Metrics: API performance, ML predictions, blockchain transactions
- Alerts: System health, error rates, resource usage

### Prometheus Alerts
- Configuration: `ops/prometheus_enhanced_alerts.yml`
- Coverage: Critical system failures, performance degradation, security events

## 🧪 Testing

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Specific component tests
python -m pytest tests/unit/test_enhanced_telemetry_validation.py -v
python -m pytest tests/unit/test_enhanced_ml_inference.py -v
python -m pytest tests/unit/test_enhanced_blockchain_integration.py -v
```

## 🔒 Security Features

- **Authentication**: JWT, API keys, client certificates
- **Authorization**: Role-based access control (RBAC)
- **Rate Limiting**: Per-user/device request throttling
- **Input Validation**: Comprehensive schema validation
- **Secrets Management**: Environment variable configuration
- **HTTPS Ready**: SSL/TLS support for production

## 🚀 Production Deployment

### Docker Deployment
```bash
# Build images
docker-compose -f docker-compose.enhanced.yml build

# Start services
docker-compose -f docker-compose.enhanced.yml up -d
```

### Kubernetes Deployment
```bash
# Deploy to Kubernetes
kubectl apply -f infra/k8s/

# Check status
kubectl get pods -n transport-system
```

## 📚 API Documentation

- **ML Services**: http://localhost:5002/docs (FastAPI auto-generated)
- **Main API**: Available via OpenAPI spec in `openapi/api.yaml`
- **WebSocket Events**: Documented in `api_server/websocket_manager.py`

## 🎯 Demo Flow

1. **System Startup**: All services start with health monitoring
2. **Vehicle Simulation**: Multiple vehicles generate realistic telemetry
3. **Real-time Processing**: Stream validation, ML predictions, map matching
4. **Dashboard Updates**: Live vehicle tracking, risk alerts, system metrics
5. **Toll Events**: Automatic toll detection and blockchain transactions
6. **Monitoring**: Grafana dashboards show system performance

## 🔍 Troubleshooting

### Common Issues
- **Port Conflicts**: Check if ports 5000-5004, 6379, 1883 are available
- **Dependencies**: Ensure all Python packages are installed
- **Services**: Verify Redis and MQTT broker are running
- **Permissions**: Check file permissions for database and logs

### Logs
```bash
# Service logs
tail -f logs/api_server.log
tail -f logs/ml_services.log
tail -f logs/blockchain.log

# System status
python start_enhanced_prototype.py --status
```

## 📄 License

MIT License - See LICENSE file for details