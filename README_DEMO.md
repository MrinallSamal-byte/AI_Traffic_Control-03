# Smart Transportation System - ML Driver Scoring Demo

This demo shows the end-to-end ML-based driver scoring system with a trained model, API server, and vehicle simulator.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Train the ML Model

```bash
python ml_services/train_model.py
```

Expected output:
```
Generating synthetic training data...
Training RandomForest model...
Train R²: 0.9234
Test R²: 0.8567
Model saved to ml_services\model.pkl
```

### 3. Start the API Server

```bash
python api_server/app.py
```

Expected output:
```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://[::1]:5000
```

### 4. Run the Vehicle Simulator (in another terminal)

```bash
python device_simulator/simulator.py --devices 3 --interval 1 --mode http
```

Expected output:
```
🚗 Starting 3 vehicle simulators in http mode...
✓ Device OBU-12345678 connected to HTTP API
✓ Device OBU-87654321 connected to HTTP API  
✓ Device OBU-11223344 connected to HTTP API
📡 OBU-12345678: Speed 52.3 km/h -> Score: 23.4 (random_forest)
📡 OBU-87654321: Speed 48.1 km/h -> Score: 18.7 (random_forest)
📡 OBU-11223344: Speed 55.9 km/h -> Score: 31.2 (random_forest)
```

### 5. Run Tests

```bash
pytest -q
```

Expected output:
```
.......                                                          [100%]
7 passed in 0.45s
```

## API Endpoints

### Health Check
```bash
curl http://localhost:5000/health
```

### Driver Score
```bash
curl -X POST http://localhost:5000/driver_score \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test_vehicle",
    "timestamp": 1699123456,
    "speed": 60.0,
    "accel_x": 2.1,
    "accel_y": 0.5,
    "accel_z": 9.8,
    "jerk": 0.8,
    "yaw": 0.03
  }'
```

Response:
```json
{
  "device_id": "test_vehicle",
  "timestamp": 1699123456,
  "driver_score": 28.7,
  "model": "random_forest"
}
```

## Model Fallback

If the model file is missing, the system automatically falls back to a heuristic scoring function:

```bash
# Delete model to test fallback
rm ml_services/model.pkl

# Restart API and test - should return "model": "heuristic"
```

## Architecture

```
Vehicle Simulator → HTTP POST → API Server → ML Model → Driver Score
                                     ↓
                              Database Storage
```

## Troubleshooting

- **Port 5000 in use**: Change port in `api_server/app.py` line: `app.run(port=5001)`
- **Model not found**: Run `python ml_services/train_model.py` to create model.pkl
- **Connection refused**: Ensure API server is running before starting simulator