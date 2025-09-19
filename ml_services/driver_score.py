import os
import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model
    if os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
            return _model
        except Exception:
            _model = None
            return None
    return None

def heuristic_score(telemetry):
    speed = float(telemetry.get("speed", 0))
    accel_x = abs(float(telemetry.get("accel_x", 0)))
    accel_y = abs(float(telemetry.get("accel_y", 0)))
    jerk = abs(float(telemetry.get("jerk", 0)))
    score = 0.02 * speed + 7.0 * accel_x + 4.0 * accel_y + 6.0 * jerk
    score = max(0.0, min(100.0, score))
    return score

def predict_score(telemetry):
    model = _load_model()
    features = [
        float(telemetry.get("speed", 0)),
        float(telemetry.get("accel_x", 0)),
        float(telemetry.get("accel_y", 0)),
        float(telemetry.get("accel_z", 9.8)),
        float(telemetry.get("jerk", 0)),
        float(telemetry.get("yaw", 0))
    ]
    if model is not None:
        try:
            pred = model.predict([features])[0]
            pred = float(max(0.0, min(100.0, pred)))
            return {"score": pred, "model": "random_forest"}
        except Exception:
            pass
    return {"score": heuristic_score(telemetry), "model": "heuristic"}