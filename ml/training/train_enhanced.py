#!/usr/bin/env python3
"""
Enhanced ML Training Script for Harsh Driving Detection
Supports multiple models and versioned model saving
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib
import json
import os
from datetime import datetime
import logging
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HarshDrivingTrainer:
    def __init__(self, models_dir="../models"):
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        
        self.scaler = StandardScaler()
        self.model = None
        self.feature_names = [
            'speed', 'accel_x', 'accel_y', 'accel_z', 'jerk', 'yaw'
        ]
    
    def generate_synthetic_data(self, n_samples=10000):
        """Generate synthetic telemetry data for training"""
        logger.info(f"Generating {n_samples} synthetic samples")
        
        np.random.seed(42)
        
        # Normal driving patterns
        normal_samples = n_samples // 2
        normal_speed = np.random.normal(50, 15, normal_samples)
        normal_accel_x = np.random.normal(0, 1.5, normal_samples)
        normal_accel_y = np.random.normal(0, 1.2, normal_samples)
        normal_accel_z = np.random.normal(9.8, 0.5, normal_samples)
        normal_jerk = np.random.normal(0, 0.8, normal_samples)
        normal_yaw = np.random.normal(0, 5, normal_samples)
        normal_labels = np.zeros(normal_samples)
        
        # Harsh driving patterns
        harsh_samples = n_samples - normal_samples
        harsh_speed = np.random.normal(70, 20, harsh_samples)
        harsh_accel_x = np.random.normal(0, 4, harsh_samples)  # Higher variance
        harsh_accel_y = np.random.normal(0, 3.5, harsh_samples)
        harsh_accel_z = np.random.normal(9.8, 1, harsh_samples)
        harsh_jerk = np.random.normal(0, 2.5, harsh_samples)  # Higher jerk
        harsh_yaw = np.random.normal(0, 15, harsh_samples)  # More aggressive turns
        harsh_labels = np.ones(harsh_samples)
        
        # Add some extreme harsh driving events
        extreme_indices = np.random.choice(harsh_samples, harsh_samples // 10, replace=False)
        harsh_accel_x[extreme_indices] += np.random.choice([-1, 1], len(extreme_indices)) * np.random.uniform(6, 10, len(extreme_indices))
        harsh_accel_y[extreme_indices] += np.random.choice([-1, 1], len(extreme_indices)) * np.random.uniform(5, 8, len(extreme_indices))
        harsh_jerk[extreme_indices] += np.random.choice([-1, 1], len(extreme_indices)) * np.random.uniform(3, 6, len(extreme_indices))
        
        # Combine data
        features = np.column_stack([
            np.concatenate([normal_speed, harsh_speed]),
            np.concatenate([normal_accel_x, harsh_accel_x]),
            np.concatenate([normal_accel_y, harsh_accel_y]),
            np.concatenate([normal_accel_z, harsh_accel_z]),
            np.concatenate([normal_jerk, harsh_jerk]),
            np.concatenate([normal_yaw, harsh_yaw])
        ])
        
        labels = np.concatenate([normal_labels, harsh_labels])
        
        # Create DataFrame
        df = pd.DataFrame(features, columns=self.feature_names)
        df['harsh_driving'] = labels
        
        # Shuffle data
        df = df.sample(frac=1).reset_index(drop=True)
        
        logger.info(f"Generated data: {len(df)} samples, {df['harsh_driving'].sum()} harsh driving events")
        return df
    
    def load_data(self, data_path=None):
        """Load training data from file or generate synthetic data"""
        if data_path and os.path.exists(data_path):
            logger.info(f"Loading data from {data_path}")
            df = pd.read_csv(data_path)
        else:
            logger.info("No data file provided, generating synthetic data")
            df = self.generate_synthetic_data()
        
        return df
    
    def prepare_features(self, df):
        """Prepare features for training"""
        X = df[self.feature_names].copy()
        y = df['harsh_driving'].copy()
        
        # Add derived features
        X['accel_magnitude'] = np.sqrt(X['accel_x']**2 + X['accel_y']**2 + X['accel_z']**2)
        X['lateral_accel'] = np.sqrt(X['accel_x']**2 + X['accel_y']**2)
        X['speed_accel_ratio'] = X['speed'] / (X['accel_magnitude'] + 1e-6)
        
        self.feature_names_extended = X.columns.tolist()
        
        return X, y
    
    def train_model(self, X, y, model_type='random_forest'):
        """Train the model"""
        logger.info(f"Training {model_type} model")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        if model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight='balanced'
            )
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        auc_score = roc_auc_score(y_test, y_pred_proba)
        
        logger.info(f"Training accuracy: {train_score:.3f}")
        logger.info(f"Test accuracy: {test_score:.3f}")
        logger.info(f"AUC score: {auc_score:.3f}")
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5)
        logger.info(f"CV accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = dict(zip(self.feature_names_extended, self.model.feature_importances_))
            logger.info("Feature importance:")
            for feature, importance in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {feature}: {importance:.3f}")
        
        return {
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'auc_score': auc_score,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'feature_importance': feature_importance if hasattr(self.model, 'feature_importances_') else None
        }
    
    def save_model(self, model_name="harsh_driving_model", metadata=None):
        """Save model with versioning"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save versioned model
        versioned_model_path = os.path.join(self.models_dir, f"{model_name}_{timestamp}.pkl")
        versioned_metadata_path = os.path.join(self.models_dir, f"{model_name}_metadata_{timestamp}.json")
        
        # Save latest model
        latest_model_path = os.path.join(self.models_dir, f"{model_name}_latest.pkl")
        latest_metadata_path = os.path.join(self.models_dir, f"{model_name}_metadata_latest.json")
        
        # Prepare model bundle
        model_bundle = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names_extended,
            'timestamp': timestamp
        }
        
        # Save model files
        joblib.dump(model_bundle, versioned_model_path)
        joblib.dump(model_bundle, latest_model_path)
        
        # Prepare metadata
        model_metadata = {
            'model_name': model_name,
            'timestamp': timestamp,
            'feature_names': self.feature_names_extended,
            'model_type': type(self.model).__name__,
            'model_params': self.model.get_params() if hasattr(self.model, 'get_params') else {},
            'training_metadata': metadata or {}
        }
        
        # Save metadata files
        with open(versioned_metadata_path, 'w') as f:
            json.dump(model_metadata, f, indent=2)
        
        with open(latest_metadata_path, 'w') as f:
            json.dump(model_metadata, f, indent=2)
        
        logger.info(f"Model saved: {versioned_model_path}")
        logger.info(f"Latest model: {latest_model_path}")
        
        return versioned_model_path, latest_model_path

def main():
    parser = argparse.ArgumentParser(description='Train harsh driving detection model')
    parser.add_argument('--data', type=str, help='Path to training data CSV file')
    parser.add_argument('--model-type', type=str, default='random_forest', help='Model type to train')
    parser.add_argument('--samples', type=int, default=10000, help='Number of synthetic samples to generate')
    parser.add_argument('--models-dir', type=str, default='../models', help='Directory to save models')
    
    args = parser.parse_args()
    
    # Initialize trainer
    trainer = HarshDrivingTrainer(models_dir=args.models_dir)
    
    # Load or generate data
    df = trainer.load_data(args.data)
    if args.data is None:
        df = trainer.generate_synthetic_data(args.samples)
    
    # Prepare features
    X, y = trainer.prepare_features(df)
    
    # Train model
    training_results = trainer.train_model(X, y, args.model_type)
    
    # Save model
    trainer.save_model("harsh_driving_model", training_results)
    
    logger.info("Training completed successfully!")

if __name__ == "__main__":
    main()