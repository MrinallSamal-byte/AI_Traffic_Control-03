#!/usr/bin/env python3
"""
ML Services API - Inference endpoints with model versioning
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required
import os
import sys
import logging
import time
import joblib
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# Model management
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

class ModelManager:
    def __init__(self):
        self.current_model = None
        self.model_version = None
        self.model_metadata = {}
        self.load_latest_model()
    
    def load_latest_model(self):
        """Load the latest model version"""
        try:
            # Look for versioned models
            model_files = list(MODEL_DIR.glob("driver_model_v*.pkl"))
            if model_files:
                # Get latest version
                latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
                self.current_model = joblib.load(latest_model)
                self.model_version = latest_model.stem
                
                # Load metadata if exists
                metadata_file = latest_model.with_suffix('.json')
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        self.model_metadata = json.load(f)
                
                logger.info(f"Loaded model: {self.model_version}")
            else:
                # Fallback to legacy model
                legacy_model = Path(__file__).parent / "model.pkl"
                if legacy_model.exists():
                    self.current_model = joblib.load(legacy_model)
                    self.model_version = "legacy"
                    logger.info("Loaded legacy model")
                else:
                    logger.warning("No model found, using heuristic")
        except Exception as e:
            logger.error(f"Model loading error: {e}")
    
    def predict(self, features):
        """Make prediction with current model"""
        if self.current_model:
            try:
                prediction = self.current_model.predict([features])[0]
                return {
                    "score": float(max(0.0, min(100.0, prediction))),
                    "model": self.model_version,
                    "confidence": 0.85  # Mock confidence
                }
            except Exception as e:
                logger.error(f"Prediction error: {e}")
        
        # Fallback to heuristic
        return self._heuristic_predict(features)
    
    def _heuristic_predict(self, features):
        """Heuristic prediction fallback"""
        speed, accel_x, accel_y, accel_z, jerk, yaw = features
        score = 0.02 * speed + 7.0 * abs(accel_x) + 4.0 * abs(accel_y) + 6.0 * abs(jerk)
        return {
            "score": float(max(0.0, min(100.0, score))),
            "model": "heuristic",
            "confidence": 0.6
        }
    
    def save_model(self, model, version_name, metadata=None):
        """Save model with version and metadata"""
        try:
            model_path = MODEL_DIR / f"driver_model_{version_name}.pkl"
            joblib.dump(model, model_path)
            
            if metadata:
                metadata_path = model_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            logger.info(f"Model saved: {version_name}")
            return True
        except Exception as e:
            logger.error(f"Model save error: {e}")
            return False

model_manager = ModelManager()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ml_services',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'model_version': model_manager.model_version,
        'model_loaded': model_manager.current_model is not None
    })

@app.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    """ML inference endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "invalid json"}), 400
        
        # Extract features
        features = [
            float(data.get("speed", 0)),
            float(data.get("accel_x", 0)),
            float(data.get("accel_y", 0)),
            float(data.get("accel_z", 9.8)),
            float(data.get("jerk", 0)),
            float(data.get("yaw", 0))
        ]
        
        # Make prediction
        result = model_manager.predict(features)
        
        # Add request metadata
        result.update({
            "device_id": data.get("device_id"),
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat() + 'Z'),
            "prediction_time": datetime.utcnow().isoformat() + 'Z'
        })
        
        # Determine alert level
        score = result["score"]
        if score > 80:
            result["alert"] = "HIGH_RISK"
        elif score > 60:
            result["alert"] = "MEDIUM_RISK"
        else:
            result["alert"] = "NORMAL"
        
        logger.info(f"Prediction made", extra={
            'device_id': data.get('device_id'),
            'score': score,
            'alert': result["alert"],
            'model': result["model"]
        })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": "prediction failed"}), 500

@app.route('/model/info', methods=['GET'])
def model_info():
    """Get current model information"""
    return jsonify({
        'version': model_manager.model_version,
        'metadata': model_manager.model_metadata,
        'loaded': model_manager.current_model is not None
    })

@app.route('/model/reload', methods=['POST'])
@jwt_required()
def reload_model():
    """Reload model (for hot-swapping)"""
    try:
        model_manager.load_latest_model()
        return jsonify({
            'status': 'reloaded',
            'version': model_manager.model_version
        })
    except Exception as e:
        logger.error(f"Model reload error: {e}")
        return jsonify({'error': 'reload failed'}), 500

if __name__ == "__main__":
    logger.info("Starting ML Services API on port 5001")
    app.run(host='0.0.0.0', port=5001, debug=True)