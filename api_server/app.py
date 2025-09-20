#!/usr/bin/env python3
"""
API Server - MVP Prototype for Smart Transportation System
Simplified version with essential endpoints for ML model demo
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from datetime import datetime
import logging

# Add ml_services to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml_services.driver_score import predict_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'api_server'
    })

# Driver scoring endpoint
@app.route('/driver_score', methods=['POST'])
def driver_score():
    """Calculate driver score from telemetry data"""
    try:
        telemetry = request.get_json()
        if not telemetry:
            return jsonify({"error": "invalid json"}), 400
        
        # Validate required fields
        required_fields = ['device_id', 'timestamp']
        for field in required_fields:
            if field not in telemetry:
                return jsonify({"error": f"missing field: {field}"}), 400
        
        # Get driver score from ML service
        score_result = predict_score(telemetry)
        
        # Log the request
        logger.info(f"Driver score request: device_id={telemetry.get('device_id')}, score={score_result['score']:.2f}")
        
        response = {
            "device_id": telemetry.get("device_id"),
            "timestamp": telemetry.get("timestamp"),
            "driver_score": score_result["score"],
            "model": score_result["model"]
        }
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Driver score error: {e}")
        return jsonify({"error": "internal error"}), 500

if __name__ == "__main__":
    logger.info("Starting API server on port 5000")
    app.run(host='0.0.0.0', port=5000, debug=True)