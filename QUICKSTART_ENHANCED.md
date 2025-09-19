# Smart Transportation System - Enhanced Quick Start

## 🚀 New Features Overview

### Core System Updates
- **Telemetry Replay & Stress Testing**: Replay stored data and test with 10,000+ vehicles
- **Enhanced Stream Processing**: Dead-letter queue, rate limiting, event enrichment
- **ML Model Improvements**: Model versioning, drift detection, ensemble models
- **GraphQL API**: Flexible query interface for complex data retrieval
- **Security Upgrades**: JWT auth, role-based access, SQL injection protection
- **Comprehensive Monitoring**: Prometheus metrics, structured logging, alerts

## 🛠️ Prerequisites

```bash
# Required software
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend)
- Git

# Verify installation
python --version
docker --version
docker-compose --version
node --version
```

## ⚡ Quick Start (5 minutes)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd Protopype
pip install -r requirements.txt
```

### 2. Start Complete System
```bash
# Start everything (infrastructure + services + simulator)
python start_system.py

# Or start without simulator
python start_system.py --no-simulator

# Or start with custom vehicle count
python start_system.py --vehicles 10
```

### 3. Access Dashboards
- **Main Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:5000/api/v1
- **GraphQL Playground**: http://localhost:5002/graphql
- **Monitoring**: http://localhost:8000/metrics
- **Health Check**: http://localhost:5000/health

## 🧪 Testing & Validation

### Stress Testing
```bash
# Test with 1,000 vehicles for 5 minutes
python tools/stress_test.py --vehicles 1000 --duration 300

# Test with 10,000 vehicles (system limits)
python tools/stress_test.py --vehicles 10000 --duration 600
```

### Security Testing
```bash
# Run comprehensive security scan
python tools/security/security_scanner.py

# Check for SQL injection, XSS, auth bypass
# Results saved to security_report.json
```

### Telemetry Replay
```bash
# Replay last hour of data at 2x speed
python tools/telemetry_replay.py --hours 1 --speed 2.0

# Replay specific device data
python tools/telemetry_replay.py --device-id OBU-001 --speed 0.5
```

## 📊 API Examples

### REST API
```bash
# Get all vehicles
curl http://localhost:5000/api/v1/vehicles

# Get driver score
curl http://localhost:5000/api/v1/vehicles/{id}/score

# Get toll transactions
curl http://localhost:5000/api/v1/vehicles/{id}/transactions
```

### GraphQL API
```graphql
# Query vehicle with telemetry
query {
  vehicle(vehicle_id: "123") {
    registration_no
    balance
  }
  telemetry(device_id: "OBU-001", limit: 10) {
    timestamp
    location { lat lon }
    speed_kmph
  }
}
```

## 🔧 Advanced Configuration

### Environment Variables
```bash
# Database
export DATABASE_URL="postgresql://admin:password@localhost:5432/transport_system"

# Redis
export REDIS_URL="redis://localhost:6379"

# Kafka
export KAFKA_BROKERS="localhost:9092"

# MQTT
export MQTT_BROKER="localhost:1883"
```

### Rate Limiting Configuration
```python
# In stream_processor/processor.py
config = {
    'rate_limit': {
        'messages_per_minute': 120  # Increase for high-throughput
    }
}
```

### ML Model Configuration
```python
# In ml_services/model_manager.py
model_manager = ModelManager(
    model_registry_uri="sqlite:///mlflow.db",
    drift_threshold=0.15  # Adjust sensitivity
)
```

## 📱 Mobile App (Flutter)

### Setup Flutter Environment
```bash
# Install Flutter SDK
# Add to PATH: flutter/bin

# Verify installation
flutter doctor

# Run mobile app
cd mobile_app
flutter pub get
flutter run
```

### Mobile Features
- Real-time driver score monitoring
- Toll charge notifications
- Transaction history
- Wallet balance tracking

## 🔍 Monitoring & Observability

### Prometheus Metrics
```bash
# Access metrics endpoint
curl http://localhost:8000/metrics

# Key metrics:
# - api_requests_total
# - telemetry_messages_total
# - ml_predictions_total
# - system_cpu_percent
# - kafka_consumer_lag
```

### Structured Logging
```bash
# View logs with correlation IDs
tail -f logs/transport_system.log | jq '.'

# Filter by correlation ID
grep "correlation_id" logs/transport_system.log
```

### Alerts Configuration
```python
# In ops/monitoring/metrics_collector.py
alert_rules = {
    'high_cpu': {'threshold': 80, 'duration': 300},
    'high_memory': {'threshold': 85, 'duration': 300},
    'high_api_latency': {'threshold': 2.0, 'duration': 60}
}
```

## 🛡️ Security Features

### Authentication & Authorization
```bash
# Login to get JWT token
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'

# Use token in requests
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/v1/admin/dashboard
```

### Role-Based Access Control
- **Admin**: Full system access, user management
- **Operator**: Toll management, monitoring
- **User**: Own vehicle data only

### Input Validation & Sanitization
- SQL injection protection
- XSS prevention
- Input type validation
- Rate limiting per user/IP

## 🚀 Deployment Options

### Docker Production
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy with scaling
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

### Kubernetes (Helm)
```bash
# Install with Helm
cd infra/k8s/helm
helm install transport-system ./transport-system

# Scale services
kubectl scale deployment api-server --replicas=5
```

### Cloud Deployment (Terraform)
```bash
# Deploy to AWS/GCP/Azure
cd infra/terraform
terraform init
terraform plan
terraform apply
```

## 🔧 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check Docker services
docker-compose ps

# Check logs
docker-compose logs -f

# Restart specific service
docker-compose restart postgres
```

**High memory usage:**
```bash
# Check system resources
python -c "
import psutil
print(f'CPU: {psutil.cpu_percent()}%')
print(f'Memory: {psutil.virtual_memory().percent}%')
"
```

**Database connection issues:**
```bash
# Test database connection
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://admin:password@localhost:5432/transport_system')
print('Database connection successful')
"
```

### Performance Tuning

**For high-throughput scenarios:**
1. Increase Kafka partitions
2. Scale stream processors
3. Optimize database indexes
4. Enable connection pooling
5. Use Redis clustering

**For low-latency requirements:**
1. Reduce batch sizes
2. Increase processing frequency
3. Use SSD storage
4. Optimize network configuration

## 📈 Scaling Guidelines

### Horizontal Scaling
- **API Servers**: 3-5 instances behind load balancer
- **Stream Processors**: 1 per Kafka partition
- **ML Services**: 2-3 instances for redundancy

### Vertical Scaling
- **Database**: 8GB+ RAM, SSD storage
- **Kafka**: 4GB+ RAM per broker
- **Redis**: 2GB+ RAM for caching

### Monitoring Thresholds
- **CPU**: Alert at 80%, scale at 85%
- **Memory**: Alert at 85%, scale at 90%
- **API Latency**: Alert at 2s, scale at 3s
- **Error Rate**: Alert at 5%, investigate at 1%

## 🎯 Next Steps

1. **Customize for your use case**: Modify vehicle types, toll pricing, road networks
2. **Integrate with external systems**: Government APIs, payment gateways, traffic systems
3. **Add advanced features**: AI-powered traffic optimization, predictive maintenance
4. **Scale for production**: Implement proper CI/CD, monitoring, backup strategies

## 📞 Support

- **Documentation**: Check README files in each component directory
- **Issues**: Create GitHub issues for bugs or feature requests
- **Monitoring**: Use built-in health checks and metrics for system status
- **Logs**: Check structured logs for detailed troubleshooting information