#!/usr/bin/env python3
"""
Train baseline RandomForest model for driver behavior prediction
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import json
from datetime import datetime
from pathlib import Path

def generate_synthetic_data(n_samples=1000):
    """Generate synthetic training data"""
    np.random.seed(42)
    
    # Features: speed, accel_x, accel_y, accel_z, jerk, yaw
    speed = np.random.uniform(0, 120, n_samples)
    accel_x = np.random.normal(0, 2, n_samples)
    accel_y = np.random.normal(0, 2, n_samples)
    accel_z = np.random.normal(9.8, 1, n_samples)
    jerk = np.random.normal(0, 3, n_samples)
    yaw = np.random.uniform(-180, 180, n_samples)
    
    # Create risk score based on driving behavior
    risk_score = (
        0.1 * speed +
        5.0 * np.abs(accel_x) +
        3.0 * np.abs(accel_y) +
        4.0 * np.abs(jerk) +
        0.01 * np.abs(yaw) +
        np.random.normal(0, 5, n_samples)  # Add noise
    )
    
    # Clip to 0-100 range
    risk_score = np.clip(risk_score, 0, 100)
    
    features = np.column_stack([speed, accel_x, accel_y, accel_z, jerk, yaw])
    
    return features, risk_score

def train_model():
    """Train and save the baseline model"""
    print("Generating synthetic training data...")
    X, y = generate_synthetic_data(2000)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print("Training RandomForest model...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Performance:")
    print(f"  MSE: {mse:.2f}")
    print(f"  R²: {r2:.3f}")
    
    # Save model with version
    model_dir = Path(__file__).parent / "models"
    model_dir.mkdir(exist_ok=True)
    
    version = datetime.now().strftime("v%Y%m%d_%H%M%S")
    model_path = model_dir / f"driver_model_{version}.pkl"
    
    joblib.dump(model, model_path)
    
    # Save metadata
    metadata = {
        "version": version,
        "created_at": datetime.utcnow().isoformat() + 'Z',
        "model_type": "RandomForestRegressor",
        "features": ["speed", "accel_x", "accel_y", "accel_z", "jerk", "yaw"],
        "performance": {
            "mse": float(mse),
            "r2": float(r2),
            "n_samples": len(X_train)
        },
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 10,
            "random_state": 42
        }
    }
    
    metadata_path = model_path.with_suffix('.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Model saved: {model_path}")
    print(f"Metadata saved: {metadata_path}")
    
    return model, metadata

if __name__ == "__main__":
    train_model()