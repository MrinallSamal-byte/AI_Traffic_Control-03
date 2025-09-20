#!/usr/bin/env python3
"""
ML Serving API with FastAPI for driver scoring and harsh driving detection
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import joblib
import numpy as np
import os
import logging
from datetime import datetime
import time
from collections import defaultdict
import psutil
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
PREDICTION_COUNT = Counter('ml_predictions_total', 'Total ML predictions', ['model_type', 'endpoint'])
PREDICTION_DURATION = Histogram('ml_prediction_duration_seconds', 'ML prediction duration', ['model_type'])
MODEL_LOAD_COUNT = Counter('ml_model_loads_total', 'Total model loads', ['model_name'])
ERROR_COUNT = Counter('ml_errors_total', 'Total ML errors', ['error_type'])
ACTIVE_MODELS = Gauge('ml_active_models', 'Number of loaded models')

app = FastAPI(
    title="ML Services API",
    description="Machine Learning services for Smart Transportation System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics tracking
metrics = {
    'request_count': defaultdict(int),
    'error_count': defaultdict(int),
    'response_times': defaultdict(list),
    'model_predictions': defaultdict(int)
}

# Model cache
models = {}

class TelemetryInput(BaseModel):
    """Input schema for telemetry data"""
    deviceId: str = Field(..., description="Device identifier")
    speed: float = Field(..., ge=0, le=300, description="Speed in km/h")
    accel_x: float = Field(..., ge=-50, le=50, description="X-axis acceleration")
    accel_y: float = Field(..., ge=-50, le=50, description="Y-axis acceleration")
    accel_z: float = Field(..., ge=-50, le=50, description="Z-axis acceleration")
    jerk: float = Field(0.0, ge=-20, le=20, description="Jerk (rate of acceleration change)")
    yaw: float = Field(0.0, ge=-180, le=180, description="Yaw rate")
    timestamp: Optional[str] = Field(None, description="Timestamp")

class PredictionResponse(BaseModel):
    """Response schema for predictions"""
    deviceId: str
    prediction: float
    model_version: str
    confidence: Optional[float] = None
    timestamp: str
    processing_time_ms: float

def load_model(model_name: str):
    """Load model from disk with caching"""
    if model_name in models:
        return models[model_name]
    
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'ml', 'models')
    model_path = os.path.join(models_dir, f'{model_name}_latest.pkl')
    
    if not os.path.exists(model_path):
        # Fallback to legacy model path
        legacy_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
        if os.path.exists(legacy_path):
            model_path = legacy_path
        else:
            raise FileNotFoundError(f"Model not found: {model_name}")
    
    try:
        model = joblib.load(model_path)
        models[model_name] = {
            'model': model,
            'loaded_at': datetime.now(),
            'path': model_path
        }
        logger.info(f"Loaded model: {model_name} from {model_path}")
        return models[model_name]
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        raise

def heuristic_score(telemetry: TelemetryInput) -> float:
    """Fallback heuristic scoring when ML model is unavailable"""
    speed = float(telemetry.speed)
    accel_x = abs(float(telemetry.accel_x))
    accel_y = abs(float(telemetry.accel_y))
    jerk = abs(float(telemetry.jerk))
    
    # Simple heuristic formula
    score = 0.02 * speed + 7.0 * accel_x + 4.0 * accel_y + 6.0 * jerk
    score = max(0.0, min(100.0, score))
    return score

@app.middleware("http")
async def track_metrics(request, call_next):
    """Middleware to track request metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = (time.time() - start_time) * 1000  # Convert to milliseconds
    endpoint = request.url.path
    
    # Track metrics
    metrics['request_count'][endpoint] += 1
    metrics['response_times'][endpoint].append(duration)
    
    if response.status_code >= 400:
        metrics['error_count'][endpoint] += 1
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ml_services",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "models_loaded": list(models.keys()),
        "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
        "cpu_percent": psutil.Process().cpu_percent()
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    # Update active models gauge
    ACTIVE_MODELS.set(len(models))
    
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/metrics/json")
async def get_metrics():
    """Get service metrics for monitoring in JSON format"""
    return {
        "request_count": dict(metrics['request_count']),
        "error_count": dict(metrics['error_count']),
        "avg_response_time_ms": {
            endpoint: sum(times) / len(times) if times else 0
            for endpoint, times in metrics['response_times'].items()
        },
        "model_predictions": dict(metrics['model_predictions']),
        "models_loaded": len(models),
        "uptime_seconds": time.time() - app.start_time if hasattr(app, 'start_time') else 0
    }

@app.post("/predict/driver_score", response_model=PredictionResponse)
async def predict_driver_score(telemetry: TelemetryInput):
    """Predict driver score from telemetry data"""
    start_time = time.time()
    
    try:
        # Prepare features
        features = [
            telemetry.speed,
            telemetry.accel_x,
            telemetry.accel_y,
            telemetry.accel_z,
            telemetry.jerk,
            telemetry.yaw
        ]
        
        # Try to use ML model
        try:
            model_info = load_model('harsh_driving_model')
            model = model_info['model']
            
            # Predict harsh driving probability
            prediction_proba = model.predict_proba([features])[0]
            harsh_probability = prediction_proba[1] if len(prediction_proba) > 1 else 0.0
            
            # Convert to driver score (inverse of harsh driving probability)
            driver_score = (1.0 - harsh_probability) * 100.0
            model_version = "random_forest_v1"
            confidence = max(prediction_proba)
            
            metrics['model_predictions']['ml_model'] += 1
            
        except Exception as e:
            logger.warning(f"ML model prediction failed, using heuristic: {e}")
            driver_score = heuristic_score(telemetry)
            model_version = "heuristic_v1"
            confidence = None
            metrics['model_predictions']['heuristic'] += 1
        
        processing_time = (time.time() - start_time) * 1000
        
        return PredictionResponse(
            deviceId=telemetry.deviceId,
            prediction=round(driver_score, 2),
            model_version=model_version,
            confidence=round(confidence, 3) if confidence else None,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")

@app.post("/predict/harsh_driving", response_model=PredictionResponse)
async def predict_harsh_driving(telemetry: TelemetryInput):
    """Predict harsh driving behavior from telemetry data"""
    start_time = time.time()
    
    try:
        # Prepare features
        features = [
            telemetry.speed,
            telemetry.accel_x,
            telemetry.accel_y,
            telemetry.accel_z,
            telemetry.jerk,
            telemetry.yaw
        ]
        
        try:
            model_info = load_model('harsh_driving_model')
            model = model_info['model']
            
            # Predict harsh driving probability
            prediction_proba = model.predict_proba([features])[0]
            harsh_probability = prediction_proba[1] if len(prediction_proba) > 1 else 0.0
            
            model_version = "random_forest_v1"
            confidence = max(prediction_proba)
            
            metrics['model_predictions']['ml_model'] += 1
            
        except Exception as e:
            logger.warning(f"ML model prediction failed, using heuristic: {e}")
            # Simple heuristic for harsh driving detection
            harsh_score = (abs(telemetry.accel_x) + abs(telemetry.accel_y) + abs(telemetry.jerk)) / 3
            harsh_probability = min(harsh_score / 10.0, 1.0)  # Normalize to 0-1
            model_version = "heuristic_v1"
            confidence = None
            metrics['model_predictions']['heuristic'] += 1
        
        processing_time = (time.time() - start_time) * 1000
        
        return PredictionResponse(
            deviceId=telemetry.deviceId,
            prediction=round(harsh_probability * 100, 2),  # Convert to percentage
            model_version=model_version,
            confidence=round(confidence, 3) if confidence else None,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Harsh driving prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")

@app.get("/models")
async def list_models():
    """List loaded models and their information"""
    model_info = {}
    for name, info in models.items():
        model_info[name] = {
            "loaded_at": info['loaded_at'].isoformat(),
            "path": info['path'],
            "type": str(type(info['model']).__name__)
        }
    return {"models": model_info}

@app.post("/models/{model_name}/reload")
async def reload_model(model_name: str):
    """Reload a specific model"""
    try:
        # Remove from cache to force reload
        if model_name in models:
            del models[model_name]
        
        # Load model
        model_info = load_model(model_name)
        
        return {
            "message": f"Model {model_name} reloaded successfully",
            "loaded_at": model_info['loaded_at'].isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to reload model: {e}")

if __name__ == "__main__":
    import uvicorn
    
    app.start_time = time.time()
    logger.info("Starting ML Services API on port 5002")
    
    uvicorn.run(
        "serve:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        log_level="info"
    )