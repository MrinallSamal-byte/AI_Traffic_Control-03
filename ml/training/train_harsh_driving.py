#!/usr/bin/env python3
"""
Training script for harsh driving detection using RandomForest baseline
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_synthetic_data(n_samples=10000):
    """Generate synthetic driving data for training"""
    np.random.seed(42)
    
    # Normal driving patterns
    normal_speed = np.random.normal(50, 15, n_samples // 2)
    normal_accel_x = np.random.normal(0, 1.5, n_samples // 2)
    normal_accel_y = np.random.normal(0, 1.0, n_samples // 2)
    normal_accel_z = np.random.normal(9.8, 0.5, n_samples // 2)
    normal_jerk = np.random.normal(0, 0.8, n_samples // 2)
    normal_yaw = np.random.normal(0, 5, n_samples // 2)
    
    # Harsh driving patterns
    harsh_speed = np.random.normal(70, 20, n_samples // 2)
    harsh_accel_x = np.random.normal(0, 4.0, n_samples // 2)  # Higher variance
    harsh_accel_y = np.random.normal(0, 3.0, n_samples // 2)  # Higher variance
    harsh_accel_z = np.random.normal(9.8, 1.0, n_samples // 2)
    harsh_jerk = np.random.normal(0, 2.5, n_samples // 2)  # Higher jerk
    harsh_yaw = np.random.normal(0, 15, n_samples // 2)  # More aggressive turns
    
    # Add some extreme values for harsh driving
    harsh_accel_x[::10] = np.random.choice([-8, -6, 6, 8], len(harsh_accel_x[::10]))
    harsh_accel_y[::15] = np.random.choice([-6, -4, 4, 6], len(harsh_accel_y[::15]))
    harsh_jerk[::8] = np.random.choice([-5, -3, 3, 5], len(harsh_jerk[::8]))
    
    # Combine data
    features = np.column_stack([
        np.concatenate([normal_speed, harsh_speed]),
        np.concatenate([normal_accel_x, harsh_accel_x]),
        np.concatenate([normal_accel_y, harsh_accel_y]),
        np.concatenate([normal_accel_z, harsh_accel_z]),
        np.concatenate([normal_jerk, harsh_jerk]),
        np.concatenate([normal_yaw, harsh_yaw])
    ])
    
    # Labels: 0 = normal, 1 = harsh
    labels = np.concatenate([
        np.zeros(n_samples // 2),
        np.ones(n_samples // 2)
    ])
    
    # Create DataFrame
    df = pd.DataFrame(features, columns=[
        'speed', 'accel_x', 'accel_y', 'accel_z', 'jerk', 'yaw'
    ])
    df['harsh_driving'] = labels
    
    return df

def train_model(data):
    """Train RandomForest model for harsh driving detection"""
    
    # Prepare features and target
    feature_columns = ['speed', 'accel_x', 'accel_y', 'accel_z', 'jerk', 'yaw']
    X = data[feature_columns]
    y = data['harsh_driving']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train RandomForest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    logger.info("Training RandomForest model...")
    model.fit(X_train, y_train)
    
    # Evaluate model
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    logger.info(f"Training accuracy: {train_score:.3f}")
    logger.info(f"Test accuracy: {test_score:.3f}")
    
    # Detailed evaluation
    y_pred = model.predict(X_test)
    logger.info("Classification Report:")
    logger.info(f"\n{classification_report(y_test, y_pred)}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("Feature Importance:")
    logger.info(f"\n{feature_importance}")
    
    return model, {
        'train_accuracy': train_score,
        'test_accuracy': test_score,
        'feature_importance': feature_importance.to_dict('records'),
        'n_samples': len(data),
        'model_type': 'RandomForestClassifier'
    }

def save_model_artifacts(model, metadata, version=None):
    """Save model and metadata with versioning"""
    
    if version is None:
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create models directory
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    # Save model
    model_path = os.path.join(models_dir, f'harsh_driving_model_{version}.pkl')
    joblib.dump(model, model_path)
    logger.info(f"Model saved to: {model_path}")
    
    # Save metadata
    metadata_path = os.path.join(models_dir, f'harsh_driving_metadata_{version}.json')
    metadata['version'] = version
    metadata['created_at'] = datetime.now().isoformat()
    metadata['model_path'] = model_path
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved to: {metadata_path}")
    
    # Save as latest
    latest_model_path = os.path.join(models_dir, 'harsh_driving_model_latest.pkl')
    latest_metadata_path = os.path.join(models_dir, 'harsh_driving_metadata_latest.json')
    
    joblib.dump(model, latest_model_path)
    with open(latest_metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("Model artifacts saved with versioning")
    return version

def main():
    """Main training pipeline"""
    logger.info("Starting harsh driving model training...")
    
    # Generate or load training data
    logger.info("Generating synthetic training data...")
    data = generate_synthetic_data(n_samples=10000)
    
    # Train model
    model, metadata = train_model(data)
    
    # Save model artifacts
    version = save_model_artifacts(model, metadata)
    
    logger.info(f"Training completed successfully! Model version: {version}")
    
    return model, metadata

if __name__ == "__main__":
    main()