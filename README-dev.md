# Developer Guide

## Quick Start

```bash
# Setup
make install
make docker-up

# Development
make test
make lint
```

## Architecture

```
Vehicle → MQTT → Kafka → Stream Processor → Database
                    ↓
API Server ← ML Services ← Processed Data
    ↓
Frontend Dashboard
```

## Services

- **API Server** (`:5000`): REST API, auth, business logic
- **Stream Processor** (`:5001`): Real-time data processing
- **ML Services** (`:5002`): Driver scoring, predictions
- **Frontend** (`:3000`): React dashboard
- **MQTT** (`:1883`): Device telemetry ingestion
- **PostgreSQL** (`:5432`): Primary database + TimescaleDB
- **Redis** (`:6379`): Caching and sessions

## Development Workflow

1. **Feature Development**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature
   # Make changes
   make test
   make lint
   git commit -m "feat: add new feature"
   git push origin feature/your-feature
   ```

2. **Testing**:
   ```bash
   # Unit tests
   pytest tests/unit/
   
   # Integration tests
   pytest tests/integration/
   
   # E2E tests
   ./ci-scripts/run_integration_tests.sh
   ```

3. **Code Quality**:
   ```bash
   # Format code
   make format
   
   # Run linters
   make lint
   
   # Security scan
   ./tools/security/scan_deps.sh
   ```

## Environment Variables

Copy `.env.example` files and configure:

- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection  
- `MQTT_BROKER_URL`: MQTT broker
- `JWT_SECRET_KEY`: API authentication
- `BLOCKCHAIN_RPC_URL`: Ethereum node

## Debugging

- **API Server**: `python -m debugpy --listen 5678 api_server/app.py`
- **Stream Processor**: Check Kafka consumer logs
- **ML Services**: Monitor model prediction accuracy
- **Database**: Use `psql` or pgAdmin for queries

## Common Issues

- **Port conflicts**: Check `docker-compose ps` and stop conflicting services
- **Database migrations**: Run `python database/migrate.py`
- **MQTT connection**: Verify broker is running on port 1883