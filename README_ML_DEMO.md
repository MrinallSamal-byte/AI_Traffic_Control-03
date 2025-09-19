# ML Driver Scoring Demo

Quick setup for the ML driver scoring system prototype.

## Quick Start (Copy & Paste)

1. **Train the model:**
```bash
python ml_services/train_model.py
```

2. **Start API server:**
```bash
python api_server/app.py
```

3. **Test the system:**
```bash
python test_ml_system.py
```

4. **Run simulator (in new terminal):**
```bash
python device_simulator/simple_simulator.py --devices 3 --interval 1
```

## Expected Output

**Training:**
```
Train R2: 0.95
Test R2 : 0.89
Saved model to ml_services/model.pkl
```

**Simulator:**
```
Simulating devices: ['a1b2c3d4', 'e5f6g7h8', 'i9j0k1l2']
2024-01-15T10:30:45 | a1b2c3d4 -> score=23.45 model=random_forest
2024-01-15T10:30:46 | e5f6g7h8 -> score=67.89 model=random_forest
```

## Files Created

- `ml_services/train_model.py` - ML training script
- `ml_services/driver_score.py` - Score prediction service  
- `device_simulator/simple_simulator.py` - API test simulator
- `test_ml_system.py` - Quick API test

## API Endpoint

**POST /driver_score**
```json
{
  "device_id": "test-001",
  "speed": 65.5,
  "accel_x": 2.1,
  "accel_y": -0.5,
  "accel_z": 9.8,
  "jerk": 0.8,
  "yaw": 0.02
}
```

**Response:**
```json
{
  "device_id": "test-001",
  "driver_score": 45.67,
  "model": "random_forest"
}
```