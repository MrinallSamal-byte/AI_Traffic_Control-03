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

1. **Setup Environment**:
   ```bash
   pip install -r requirements.txt
   docker-compose up -d
   ```

2. **Run Device Simulator**:
   ```bash
   python device_simulator/simulator.py
   ```

3. **Start API Server**:
   ```bash
   python api_server/app.py
   ```

4. **Access Dashboard**:
   ```
   http://localhost:3000
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