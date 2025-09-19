#!/usr/bin/env python3
"""Driver scoring model training pipeline."""

import argparse
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import mlflow
import mlflow.sklearn
from datetime import datetime
import os


def generate_synthetic_data(n_samples=10000):
    """Generate synthetic driving data for training."""
    np.random.seed(42)
    
    # Generate features
    speed_variance = np.random.normal(0, 5, n_samples)
    harsh_braking = np.random.poisson(2, n_samples)
    harsh_acceleration = np.random.poisson(1.5, n_samples)
    speeding_violations = np.random.poisson(0.5, n_samples)
    night_driving_ratio = np.random.beta(2, 5, n_samples)
    
    # Calculate driver score (0-100)
    base_score = 85
    score = (base_score 
             - speed_variance * 0.5
             - harsh_braking * 2
             - harsh_acceleration * 1.5
             - speeding_violations * 5
             - (1 - night_driving_ratio) * 10)
    
    score = np.clip(score, 0, 100)
    
    data = pd.DataFrame({
        'speed_variance': speed_variance,
        'harsh_braking_count': harsh_braking,
        'harsh_acceleration_count': harsh_acceleration,
        'speeding_violations': speeding_violations,
        'night_driving_ratio': night_driving_ratio,
        'driver_score': score
    })
    
    return data


def train_model(data, model_name="driver_scoring_model"):
    """Train driver scoring model."""
    
    # Prepare features and target
    features = ['speed_variance', 'harsh_braking_count', 'harsh_acceleration_count', 
                'speeding_violations', 'night_driving_ratio']
    X = data[features]
    y = data['driver_score']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Start MLflow run
    with mlflow.start_run():
        # Train model
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_train, y_train)
        
        # Make predictions
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Log parameters and metrics
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("max_depth", 10)
        mlflow.log_metric("mse", mse)
        mlflow.log_metric("r2_score", r2)
        
        # Log model
        mlflow.sklearn.log_model(model, "model")
        
        # Save model locally
        model_path = f"../models/{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(model, model_path)
        
        print(f"Model trained successfully!")
        print(f"MSE: {mse:.4f}")
        print(f"R² Score: {r2:.4f}")
        print(f"Model saved to: {model_path}")
        
        return model, model_path


def main():
    parser = argparse.ArgumentParser(description='Train driver scoring model')
    parser.add_argument('--epochs', type=int, default=100, help='Number of epochs')
    parser.add_argument('--dataset', type=str, default='synthetic', help='Dataset to use')
    parser.add_argument('--samples', type=int, default=10000, help='Number of synthetic samples')
    
    args = parser.parse_args()
    
    # Set MLflow tracking URI
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000'))
    mlflow.set_experiment("driver_scoring")
    
    print("Generating training data...")
    if args.dataset == 'synthetic':
        data = generate_synthetic_data(args.samples)
    else:
        # Load real dataset
        data = pd.read_csv(args.dataset)
    
    print(f"Training with {len(data)} samples...")
    model, model_path = train_model(data)
    
    print("Training completed successfully!")


if __name__ == "__main__":
    main()