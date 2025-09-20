# Smart Transportation System - MVP Quickstart

This guide shows how to run the local ML model + API + simulator demo.

## Prerequisites

- Python 3.8+
- Git

## Quick Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Train the ML model**:
   ```bash
   python ml_services/train_model.py
   ```
   Expected output:
   ```
   Generating synthetic training data...
   Training RandomForest model...
   Train R²: 0.9xxx
   Test R²: 0.8xxx
   Model saved to ml_services/model.pkl
   ```

3. **Start the API server**:
   ```bash
   python api_server/app.py
   ```
   Server will start on http://localhost:5000

4. **Run the device simulator** (in a new terminal):
   ```bash
   python device_simulator/simulator.py --devices 3
   ```
   Expected output:
   ```
   12:34:56 | OBU-abc123 -> score=45.67 model=random_forest
   12:34:57 | OBU-def456 -> score=23.45 model=random_forest
   ```

5. **View the dashboard**:
   ```bash
   python -m http.server 3000
   ```
   Then open: http://localhost:3000/dashboard/simple_demo.html

## API Endpoints

- `GET /health` → `{"status":"ok", "service":"api_server"}`
- `POST /driver_score` → Accepts telemetry JSON, returns driver score

## Testing

Run the unit tests:
```bash
python tests/test_api_driver_score.py
```

Or with pytest:
```bash
pytest tests/test_api_driver_score.py -v
```

## Expected Demo Flow

1. Simulator sends telemetry to API every second
2. API calculates driver score using ML model
3. Console shows: `timestamp | device_id -> score=XX.XX model=random_forest`
4. Dashboard displays real-time scores and statistics

## Troubleshooting

- **Model not found**: Run `python ml_services/train_model.py` first
- **API connection failed**: Check if API server is running on port 5000
- **Dashboard not loading**: Use `python -m http.server 3000` to serve files

## Sample Telemetry Format

```json
{
  "device_id": "OBU-123",
  "timestamp": 1640995200,
  "speed": 50.0,
  "accel_x": 1.2,
  "accel_y": 0.3,
  "accel_z": 9.8,
  "jerk": 0.5,
  "yaw": 0.02
}
```

## Sample API Response

```json
{
  "device_id": "OBU-123",
  "timestamp": 1640995200,
  "driver_score": 45.67,
  "model": "random_forest"
}
```