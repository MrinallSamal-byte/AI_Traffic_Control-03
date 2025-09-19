# AI Traffic Control - Driver Scoring Prototype

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Train ML Model
```bash
python ml_services/train_model.py
```
Expected output:
```
Generating synthetic training data...
Training RandomForest model...
Train R²: 0.9876
Test R²: 0.9234
Model saved to ml_services/model.pkl
```

### 3. Start API Server
```bash
python api_server/app.py
```
Expected output:
```
Database initialized successfully
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

### 4. Start Device Simulators (New Terminal)
```bash
python device_simulator/simulator.py --devices 3 --interval 1 --mode http
```
Expected output:
```
🚗 Starting 3 vehicle simulators in http mode...
✓ Device OBU-a1b2c3d4 connected to HTTP API
📡 OBU-a1b2c3d4: Speed 45.2 km/h -> Score: 23.4 (random_forest)
📡 OBU-e5f6g7h8: Speed 52.1 km/h -> Score: 31.7 (heuristic)
```

### 5. Open Dashboard
Open `frontend/demo.html` in your browser or serve it:
```bash
cd frontend
python -m http.server 8080
# Then open http://localhost:8080/demo.html
```

## Test API Manually

### Test Driver Score Endpoint
```bash
curl -X POST http://localhost:5000/driver_score \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev1","timestamp":1690000000,"speed":85,"accel_x":1.2,"accel_y":0.2,"accel_z":9.8,"jerk":0.4,"yaw":0.02}'
```

Expected response:
```json
{
  "device_id": "dev1",
  "timestamp": 1690000000,
  "driver_score": 34.7,
  "model": "random_forest"
}
```

### Get Recent Scores
```bash
curl http://localhost:5000/scores?limit=10
```

## Run Tests
```bash
pytest tests/test_driver_score.py tests/test_api_smoke.py -v
```

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Device Simulator│───▶│  API Server  │───▶│   Database      │
│ (HTTP Mode)     │    │  (Flask)     │    │ (SQLite/PG)     │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   ML Services   │
                       │ (Driver Score)  │
                       └─────────────────┘
```

## What This Demonstrates

1. **ML Model Training**: Synthetic data generation and RandomForest training
2. **Real-time Scoring**: HTTP API accepts telemetry and returns driver risk scores
3. **Database Persistence**: Telemetry and scores stored in local database
4. **Live Dashboard**: Real-time visualization of driver scores
5. **Fallback Logic**: Heuristic scoring when ML model unavailable

## Files Created/Modified

- `ml_services/train_model.py` - Enhanced ML training script
- `api_server/db.py` - Database helper with PostgreSQL/SQLite fallback
- `api_server/app.py` - Added `/driver_score` and `/scores` endpoints
- `device_simulator/simulator.py` - Added HTTP mode support
- `frontend/demo.html` - Real-time dashboard
- `tests/test_driver_score.py` - ML service unit tests
- `tests/test_api_smoke.py` - API integration tests
- `.github/workflows/prototype-tests.yml` - CI workflow