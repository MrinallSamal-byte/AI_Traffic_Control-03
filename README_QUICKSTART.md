# Smart Transportation System - Quick Start Guide

## 🚀 One-Command Startup

```bash
python start_system.py
```

This will automatically:
- Start all infrastructure services (MQTT, Kafka, PostgreSQL, Redis, Blockchain)
- Launch application services (API, ML, Stream Processor)
- Start vehicle simulators
- Serve the web dashboard

## 📊 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Web Dashboard** | http://localhost:3000 | Real-time vehicle tracking & monitoring |
| **API Server** | http://localhost:5000 | REST API endpoints |
| **ML Service** | http://localhost:5001 | Driver scoring & predictions |
| **Blockchain** | http://localhost:5002 | Smart contract interface |
| **Database** | localhost:5432 | PostgreSQL + TimescaleDB |
| **MQTT Broker** | localhost:1883 | Device telemetry ingestion |

## 🧪 Run Tests

```bash
python test_system.py
```

## 📱 Key Features Demonstrated

### 1. Vehicle Edge Simulation
- **3 simulated vehicles** publishing real-time telemetry
- GPS coordinates, speed, acceleration, CAN bus data
- Harsh driving event detection (braking, acceleration)

### 2. Real-Time Data Pipeline
- **MQTT → Kafka → Stream Processing → Database**
- Message validation and enrichment
- Event detection and alerting

### 3. AI/ML Driver Scoring
- **RandomForest model** for behavior analysis
- Real-time scoring based on driving patterns
- Event classification (harsh brake, acceleration, speeding)

### 4. Blockchain Toll Management
- **Smart contracts** for toll payments
- Automated charging based on gantry crossings
- Immutable transaction records

### 5. Interactive Dashboard
- **Live map** with vehicle positions
- Real-time event notifications
- System health monitoring
- Traffic analytics

## 🏗️ Architecture Components

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Vehicle Edge  │───▶│ MQTT Broker  │───▶│ Stream Process  │
│ (3 Simulators)  │    │   (Kafka)    │    │   (Flink)       │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                                     │
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Blockchain    │◀───│  API Gateway │◀───│   Data Layer    │
│ (Smart Contract)│    │   (Flask)    │    │ (Postgres/TS)   │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   ML Services   │
                       │ (Driver Score)  │
                       └─────────────────┘
```

## 📋 Sample API Usage

### Authentication
```bash
# Register user
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com"}'

# Response includes access_token for subsequent requests
```

### Vehicle Management
```bash
# Register vehicle
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"registration_no":"ABC123","obu_device_id":"OBU-001"}'
```

### Get Driver Score
```bash
curl -X GET http://localhost:5000/api/v1/vehicles/VEHICLE_ID/score \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Toll Operations
```bash
# Get toll gantries
curl -X GET http://localhost:5000/api/v1/toll/gantries

# Process toll charge
curl -X POST http://localhost:5000/api/v1/toll/charge \
  -H "Content-Type: application/json" \
  -d '{"vehicleId":"VID-123","gantryId":"G-001","calculatedPrice":25.00}'
```

## 🔧 Manual Service Control

If you prefer to start services individually:

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Start stream processor
python stream_processor/processor.py

# 3. Start ML service
python ml_services/driver_scoring.py

# 4. Start API server
python api_server/app.py

# 5. Start blockchain service
python blockchain/blockchain_service.py

# 6. Start vehicle simulators
python device_simulator/simulator.py --count 3

# 7. Serve dashboard
cd dashboard && python -m http.server 3000
```

## 📊 Dashboard Features

### Real-Time Map
- **Live vehicle tracking** with GPS coordinates
- **Toll gantry locations** marked on map
- **Event markers** for incidents (harsh braking, etc.)
- **Click vehicles** to see detailed telemetry

### System Monitoring
- **Active vehicle count** and status
- **Daily revenue** from toll collections
- **Alert notifications** for driving events
- **Service health** indicators

### Data Analytics
- **Driver behavior scores** trending
- **Traffic pattern analysis**
- **Revenue reporting**
- **Incident tracking**

## 🛠️ Development Notes

### Database Schema
- **Users, Vehicles, Wallets** - Core entities
- **Telemetry** - TimescaleDB hypertable for time-series data
- **Events** - Driving incidents and alerts
- **Toll Transactions** - Payment records

### MQTT Topics
```
/org/{orgId}/device/{deviceId}/telemetry  # Vehicle data
/org/{orgId}/device/{deviceId}/events     # Driving events
/org/{orgId}/device/{deviceId}/v2x        # V2X messages
/org/{orgId}/toll/{gantryId}/enter        # Toll entry
```

### ML Model Features
- Speed statistics (mean, std, max)
- Acceleration patterns (harsh events)
- Temporal features (time of day, day of week)
- Driving smoothness (jerk calculations)

## 🔒 Security Features

- **JWT authentication** for API access
- **Message signatures** for telemetry validation
- **Blockchain immutability** for toll records
- **Input validation** and sanitization

## 📈 Scalability Considerations

- **Kafka partitioning** for high-throughput telemetry
- **TimescaleDB** for efficient time-series storage
- **Microservices architecture** for independent scaling
- **Container deployment** ready for Kubernetes

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 1883, 5000-5002, 3000, 5432, 6379, 8545 are available
2. **Docker not running**: Start Docker Desktop before running the system
3. **Permission errors**: Run with appropriate permissions for Docker access
4. **Service startup delays**: Allow 30-60 seconds for all services to initialize

### Logs and Debugging

- **Service logs**: Check console output for each service
- **Database logs**: `docker-compose logs timescaledb`
- **MQTT logs**: `docker-compose logs mosquitto`
- **Test reports**: Generated in `test_report.json`

## 🎯 Next Steps for Production

1. **Security hardening**: Implement proper authentication, encryption
2. **Monitoring**: Add Prometheus/Grafana for metrics
3. **CI/CD**: Set up automated testing and deployment
4. **Load testing**: Validate performance under realistic loads
5. **Documentation**: API documentation with OpenAPI/Swagger