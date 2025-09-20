# Smart Transportation System (MVP → Production)

## Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Vehicle Edge  │───▶│ MQTT Broker  │───▶│ Stream Process  │
│ (OBU/Simulator) │    │   (Kafka)    │    │   (Flink)       │
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

## Quick Start

### Automated Setup (Recommended)
```bash
# Linux/macOS
./setup.sh

# Windows
setup.bat
```

### Manual Setup
1. **Setup Environment**:
   ```bash
   make install
   ```

2. **Start Development Environment**:
   ```bash
   make dev
   ```

3. **Access Dashboard**:
   ```
   http://localhost:3000
   ```

### Development Commands
```bash
make lint      # Run linters (Black, isort, ESLint)
make test      # Run all tests
make format    # Format code
make build     # Build Docker images
make ci        # Run CI checks locally
```

## Components

- **Device Simulator**: MQTT telemetry publisher
- **MQTT Broker**: Mosquitto with Kafka integration
- **Stream Processing**: Real-time data validation and routing
- **API Services**: REST endpoints for all operations
- **ML Pipeline**: Driver scoring and traffic prediction
- **Blockchain**: Smart contracts for toll payments
- **Dashboard**: Real-time monitoring interface
- **Database**: PostgreSQL + TimescaleDB for telemetry

## Data Flow

1. Vehicle → MQTT → Kafka → Stream Processor
2. Stream Processor → Database + ML Services
3. ML Services → API → Dashboard/Mobile
4. Toll Events → Blockchain → Payment Processing