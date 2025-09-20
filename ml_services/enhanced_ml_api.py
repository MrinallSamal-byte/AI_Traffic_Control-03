#!/usr/bin/env python3
"""
Enhanced ML Serving API with comprehensive error handling and health checks
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
import joblib
import numpy as np
import os
import logging
from datetime import datetime
import time
import asyncio
from collections import defaultdict
import psutil
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
PREDICTION_COUNT = Counter('ml_predictions_total', 'Total ML predictions', ['model_type', 'endpoint', 'status'])
PREDICTION_DURATION = Histogram('ml_prediction_duration_seconds', 'ML prediction duration', ['model_type'])
MODEL_LOAD_COUNT = Counter('ml_model_loads_total', 'Total model loads', ['model_name', 'status'])
ERROR_COUNT = Counter('ml_errors_total', 'Total ML errors', ['error_type', 'endpoint'])
ACTIVE_MODELS = Gauge('ml_active_models', 'Number of loaded models')
MODEL_MEMORY_USAGE = Gauge('ml_model_memory_mb', 'Model memory usage in MB', ['model_name'])
HEALTH_CHECK_COUNT = Counter('ml_health_checks_total', 'Total health checks', ['status'])

app = FastAPI(
    title="Enhanced ML Services API",
    description="Machine Learning services for Smart Transportation System with comprehensive monitoring",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
models_cache = {}
model_stats = defaultdict(dict)
service_start_time = time.time()

class TelemetryInput(BaseModel):
    """Enhanced input schema for telemetry data"""
    deviceId: str = Field(..., description="Device identifier", min_length=8, max_length=32)
    speed: float = Field(..., ge=0, le=300, description="Speed in km/h")
    accel_x: float = Field(..., ge=-50, le=50, description="X-axis acceleration (m/s²)")
    accel_y: float = Field(..., ge=-50, le=50, description="Y-axis acceleration (m/s²)")
    accel_z: float = Field(..., ge=-50, le=50, description="Z-axis acceleration (m/s²)")
    jerk: float = Field(0.0, ge=-20, le=20, description="Jerk (rate of acceleration change)")
    yaw_rate: float = Field(0.0, ge=-180, le=180, description="Yaw rate (deg/s)")
    heading_change: float = Field(0.0, ge=-180, le=180, description="Heading change rate")
    throttle_position: float = Field(0.0, ge=0, le=100, description="Throttle position (%)")
    brake_position: float = Field(0.0, ge=0, le=100, description="Brake position (%)")
    timestamp: Optional[str] = Field(None, description="Timestamp")
    
    @validator('deviceId')
    def validate_device_id(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Device ID must be alphanumeric with optional underscores/hyphens')
        return v

class BatchTelemetryInput(BaseModel):
    """Batch prediction input"""
    telemetry_data: List[TelemetryInput] = Field(..., description="List of telemetry data", max_items=100)
    batch_id: Optional[str] = Field(None, description="Batch identifier")

class PredictionResponse(BaseModel):
    """Enhanced response schema for predictions"""
    deviceId: str
    prediction: float
    confidence: Optional[float] = None
    model_version: str
    model_type: str
    timestamp: str
    processing_time_ms: float
    risk_level: str
    features_used: List[str]
    warnings: Optional[List[str]] = None

class BatchPredictionResponse(BaseModel):
    """Batch prediction response"""
    batch_id: str
    predictions: List[PredictionResponse]
    batch_processing_time_ms: float
    successful_predictions: int
    failed_predictions: int

class ModelInfo(BaseModel):
    """Model information schema"""
    model_name: str
    version: str
    model_type: str
    loaded_at: str
    memory_usage_mb: float
    prediction_count: int
    avg_processing_time_ms: float
    accuracy_metrics: Optional[Dict[str, float]] = None

class HealthStatus(BaseModel):
    """Health check response schema"""
    status: str
    service: str
    timestamp: str
    uptime_seconds: float
    models_loaded: int
    memory_usage_mb: float
    cpu_percent: float
    predictions_served: int
    error_rate: float

def load_model(model_name: str, force_reload: bool = False) -> Dict[str, Any]:
    """Load model with caching and error handling"""
    if model_name in models_cache and not force_reload:
        return models_cache[model_name]
    
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'ml', 'models')
    model_path = os.path.join(models_dir, f'{model_name}_latest.pkl')
    
    if not os.path.exists(model_path):
        # Try alternative paths
        alt_paths = [
            os.path.join(os.path.dirname(__file__), 'model.pkl'),
            os.path.join(models_dir, f'{model_name}.pkl')
        ]
        
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                model_path = alt_path
                break
        else:
            MODEL_LOAD_COUNT.labels(model_name=model_name, status='failed').inc()
            raise FileNotFoundError(f"Model not found: {model_name}")
    
    try:
        start_time = time.time()
        model_bundle = joblib.load(model_path)
        load_time = time.time() - start_time
        
        # Handle different model bundle formats
        if isinstance(model_bundle, dict):
            model_info = {
                'model': model_bundle.get('model'),
                'scaler': model_bundle.get('scaler'),
                'feature_names': model_bundle.get('feature_names', []),
                'metadata': model_bundle.get('metadata', {}),
                'loaded_at': datetime.now(),
                'load_time': load_time,
                'path': model_path
            }
        else:
            # Legacy format
            model_info = {
                'model': model_bundle,
                'scaler': None,
                'feature_names': [],
                'metadata': {},
                'loaded_at': datetime.now(),
                'load_time': load_time,
                'path': model_path
            }
        
        models_cache[model_name] = model_info
        model_stats[model_name] = {
            'prediction_count': 0,
            'total_processing_time': 0.0,
            'error_count': 0
        }
        
        # Update metrics
        MODEL_LOAD_COUNT.labels(model_name=model_name, status='success').inc()
        ACTIVE_MODELS.set(len(models_cache))
        
        # Estimate memory usage
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
        MODEL_MEMORY_USAGE.labels(model_name=model_name).set(memory_usage)
        
        logger.info(f"Loaded model: {model_name} in {load_time:.3f}s from {model_path}")
        return model_info
        
    except Exception as e:
        MODEL_LOAD_COUNT.labels(model_name=model_name, status='failed').inc()
        logger.error(f"Failed to load model {model_name}: {e}")
        raise

def prepare_features(telemetry: TelemetryInput) -> np.ndarray:
    """Prepare feature array from telemetry input with derived features"""
    # Base features
    features = [
        telemetry.speed,
        telemetry.accel_x,
        telemetry.accel_y,
        telemetry.accel_z,
        telemetry.jerk,
        telemetry.yaw_rate,
        telemetry.heading_change,
        telemetry.throttle_position,
        telemetry.brake_position
    ]
    
    # Derived features
    accel_magnitude = np.sqrt(telemetry.accel_x**2 + telemetry.accel_y**2 + telemetry.accel_z**2)
    lateral_accel = np.sqrt(telemetry.accel_x**2 + telemetry.accel_y**2)
    speed_accel_ratio = telemetry.speed / (accel_magnitude + 1e-6)
    brake_accel_correlation = telemetry.brake_position * abs(telemetry.accel_x)
    
    features.extend([accel_magnitude, lateral_accel, speed_accel_ratio, brake_accel_correlation])
    
    return np.array(features).reshape(1, -1)

def get_risk_level(prediction_score: float) -> str:
    """Convert prediction score to risk level"""
    if prediction_score >= 80:
        return "HIGH"
    elif prediction_score >= 60:
        return "MEDIUM"
    elif prediction_score >= 40:
        return "LOW"
    else:
        return "MINIMAL"

def heuristic_prediction(telemetry: TelemetryInput) -> Dict[str, Any]:
    """Fallback heuristic prediction when ML model fails"""
    speed = telemetry.speed
    accel_x = abs(telemetry.accel_x)
    accel_y = abs(telemetry.accel_y)
    jerk = abs(telemetry.jerk)
    brake = telemetry.brake_position
    
    # Simple heuristic scoring
    risk_score = (
        0.02 * speed +
        7.0 * accel_x +
        4.0 * accel_y +
        6.0 * jerk +
        0.3 * brake
    )
    
    risk_score = max(0.0, min(100.0, risk_score))
    
    return {
        'prediction': risk_score,
        'confidence': None,
        'model_type': 'heuristic',
        'model_version': 'heuristic_v1.0',
        'warnings': ['ML model unavailable, using heuristic fallback']
    }

@app.middleware("http")
async def track_requests(request, call_next):
    """Middleware to track request metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    endpoint = request.url.path
    
    # Update metrics based on response status
    if response.status_code < 400:
        status = 'success'
    else:
        status = 'error'
        ERROR_COUNT.labels(error_type='http_error', endpoint=endpoint).inc()
    
    return response

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Calculate metrics
        uptime = time.time() - service_start_time
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.Process().cpu_percent()
        
        # Calculate total predictions and error rate
        total_predictions = sum(stats.get('prediction_count', 0) for stats in model_stats.values())
        total_errors = sum(stats.get('error_count', 0) for stats in model_stats.values())
        error_rate = (total_errors / total_predictions) if total_predictions > 0 else 0.0
        
        HEALTH_CHECK_COUNT.labels(status='success').inc()
        
        return HealthStatus(
            status="healthy",
            service="enhanced_ml_services",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            uptime_seconds=uptime,
            models_loaded=len(models_cache),
            memory_usage_mb=memory_usage,
            cpu_percent=cpu_percent,
            predictions_served=total_predictions,
            error_rate=error_rate
        )
        
    except Exception as e:
        HEALTH_CHECK_COUNT.labels(status='error').inc()
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    ACTIVE_MODELS.set(len(models_cache))
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List all loaded models with detailed information"""
    model_list = []
    
    for model_name, model_info in models_cache.items():
        stats = model_stats.get(model_name, {})
        
        avg_processing_time = 0.0
        if stats.get('prediction_count', 0) > 0:
            avg_processing_time = stats['total_processing_time'] / stats['prediction_count']
        
        # Get accuracy metrics from metadata
        metadata = model_info.get('metadata', {})
        accuracy_metrics = {
            'test_accuracy': metadata.get('test_accuracy'),
            'auc_score': metadata.get('auc_score'),
            'cv_mean_accuracy': metadata.get('cv_mean_accuracy')
        }
        accuracy_metrics = {k: v for k, v in accuracy_metrics.items() if v is not None}
        
        model_list.append(ModelInfo(
            model_name=model_name,
            version=metadata.get('model_version', 'unknown'),
            model_type=metadata.get('model_type', 'unknown'),
            loaded_at=model_info['loaded_at'].isoformat(),
            memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024,
            prediction_count=stats.get('prediction_count', 0),
            avg_processing_time_ms=avg_processing_time * 1000,
            accuracy_metrics=accuracy_metrics if accuracy_metrics else None
        ))
    
    return model_list

@app.post("/predict", response_model=PredictionResponse)
async def predict_harsh_driving(telemetry: TelemetryInput):
    """Enhanced prediction endpoint with comprehensive error handling"""
    start_time = time.time()
    warnings = []
    
    try:
        # Prepare features
        features = prepare_features(telemetry)
        feature_names = [
            'speed_kmph', 'accel_x', 'accel_y', 'accel_z', 'jerk', 'yaw_rate',
            'heading_change', 'throttle_position', 'brake_position',
            'accel_magnitude', 'lateral_accel', 'speed_accel_ratio', 'brake_accel_correlation'
        ]
        
        try:
            # Load model
            model_info = load_model('harsh_driving_model')
            model = model_info['model']
            scaler = model_info['scaler']
            metadata = model_info['metadata']
            
            # Scale features if scaler available
            if scaler:
                features_scaled = scaler.transform(features)
            else:
                features_scaled = features
                warnings.append("No scaler available, using raw features")
            
            # Make prediction
            prediction_proba = model.predict_proba(features_scaled)[0]
            risk_score = prediction_proba[1] if len(prediction_proba) > 1 else prediction_proba[0]
            confidence = max(prediction_proba)
            
            result = {
                'prediction': risk_score * 100,  # Convert to percentage
                'confidence': confidence,
                'model_type': metadata.get('model_type', 'RandomForest'),
                'model_version': metadata.get('model_version', 'unknown'),
                'warnings': warnings if warnings else None
            }
            
            PREDICTION_COUNT.labels(model_type='ml_model', endpoint='predict', status='success').inc()
            
        except Exception as e:
            logger.warning(f"ML model prediction failed: {e}")
            result = heuristic_prediction(telemetry)
            PREDICTION_COUNT.labels(model_type='heuristic', endpoint='predict', status='fallback').inc()
        
        processing_time = (time.time() - start_time) * 1000
        
        # Update model stats
        model_name = 'harsh_driving_model' if 'ml_model' in str(result.get('model_type', '')) else 'heuristic'
        if model_name in model_stats:
            model_stats[model_name]['prediction_count'] += 1
            model_stats[model_name]['total_processing_time'] += processing_time / 1000
        
        # Record processing time metric
        PREDICTION_DURATION.labels(model_type=result['model_type']).observe(processing_time / 1000)
        
        return PredictionResponse(
            deviceId=telemetry.deviceId,
            prediction=round(result['prediction'], 2),
            confidence=round(result['confidence'], 3) if result['confidence'] else None,
            model_version=result['model_version'],
            model_type=result['model_type'],
            timestamp=datetime.utcnow().isoformat() + 'Z',
            processing_time_ms=round(processing_time, 2),
            risk_level=get_risk_level(result['prediction']),
            features_used=feature_names,
            warnings=result.get('warnings')
        )
        
    except Exception as e:
        ERROR_COUNT.labels(error_type='prediction_error', endpoint='predict').inc()
        if 'harsh_driving_model' in model_stats:
            model_stats['harsh_driving_model']['error_count'] += 1
        
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(batch_input: BatchTelemetryInput):
    """Batch prediction endpoint for multiple telemetry records"""
    start_time = time.time()
    batch_id = batch_input.batch_id or f"batch_{int(time.time())}"
    
    predictions = []
    successful = 0
    failed = 0
    
    for telemetry in batch_input.telemetry_data:
        try:
            prediction = await predict_harsh_driving(telemetry)
            predictions.append(prediction)
            successful += 1
        except Exception as e:
            logger.error(f"Batch prediction failed for device {telemetry.deviceId}: {e}")
            failed += 1
            # Continue with other predictions
    
    batch_processing_time = (time.time() - start_time) * 1000
    
    return BatchPredictionResponse(
        batch_id=batch_id,
        predictions=predictions,
        batch_processing_time_ms=round(batch_processing_time, 2),
        successful_predictions=successful,
        failed_predictions=failed
    )

@app.post("/models/{model_name}/reload")
async def reload_model(model_name: str, background_tasks: BackgroundTasks):
    """Reload a specific model"""
    try:
        # Remove from cache to force reload
        if model_name in models_cache:
            del models_cache[model_name]
        
        # Reload model in background
        background_tasks.add_task(load_model, model_name, True)
        
        return {
            "message": f"Model {model_name} reload initiated",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload model: {e}")

@app.get("/models/{model_name}/stats")
async def get_model_stats(model_name: str):
    """Get detailed statistics for a specific model"""
    if model_name not in models_cache:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model_info = models_cache[model_name]
    stats = model_stats.get(model_name, {})
    metadata = model_info.get('metadata', {})
    
    return {
        "model_name": model_name,
        "version": metadata.get('model_version', 'unknown'),
        "loaded_at": model_info['loaded_at'].isoformat(),
        "load_time_seconds": model_info.get('load_time', 0),
        "prediction_count": stats.get('prediction_count', 0),
        "error_count": stats.get('error_count', 0),
        "avg_processing_time_ms": (
            stats['total_processing_time'] / stats['prediction_count'] * 1000
            if stats.get('prediction_count', 0) > 0 else 0
        ),
        "feature_names": model_info.get('feature_names', []),
        "training_metrics": {
            "train_accuracy": metadata.get('train_accuracy'),
            "test_accuracy": metadata.get('test_accuracy'),
            "auc_score": metadata.get('auc_score'),
            "cv_mean_accuracy": metadata.get('cv_mean_accuracy')
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Enhanced ML Services API on port 5002")
    
    uvicorn.run(
        "enhanced_ml_api:app",
        host="0.0.0.0",
        port=5002,
        reload=False,
        log_level="info"
    )