#!/usr/bin/env python3
"""
Baseline ML Model Training for Harsh Driving Detection
Uses RandomForest with synthetic data for demonstration
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HarshDrivingModelTrainer:
    """Trainer for harsh driving detection model"""
    
    def __init__(self, model_version: str = None):
        self.model_version = model_version or f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_metadata = {}
        
    def generate_synthetic_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """Generate synthetic telemetry data for training"""
        np.random.seed(42)
        
        # Generate base features
        data = {
            'speed_kmph': np.random.normal(60, 20, n_samples),
            'accel_x': np.random.normal(0, 3, n_samples),
            'accel_y': np.random.normal(0, 3, n_samples), 
            'accel_z': np.random.normal(9.8, 1, n_samples),
            'jerk': np.random.normal(0, 2, n_samples),
            'yaw_rate': np.random.normal(0, 10, n_samples),
            'heading_change': np.random.normal(0, 5, n_samples),
            'throttle_position': np.random.uniform(0, 100, n_samples),
            'brake_position': np.random.uniform(0, 20, n_samples),
        }
        
        df = pd.DataFrame(data)
        
        # Clip values to realistic ranges
        df['speed_kmph'] = np.clip(df['speed_kmph'], 0, 200)
        df['accel_x'] = np.clip(df['accel_x'], -15, 15)
        df['accel_y'] = np.clip(df['accel_y'], -15, 15)
        df['accel_z'] = np.clip(df['accel_z'], 5, 15)
        df['jerk'] = np.clip(df['jerk'], -10, 10)
        df['yaw_rate'] = np.clip(df['yaw_rate'], -50, 50)
        
        # Calculate derived features
        df['accel_magnitude'] = np.sqrt(df['accel_x']**2 + df['accel_y']**2 + df['accel_z']**2)
        df['lateral_accel'] = np.sqrt(df['accel_x']**2 + df['accel_y']**2)
        df['speed_accel_ratio'] = df['speed_kmph'] / (df['accel_magnitude'] + 1e-6)
        df['brake_accel_correlation'] = df['brake_position'] * np.abs(df['accel_x'])
        
        # Generate harsh driving labels based on realistic conditions
        harsh_conditions = (
            (np.abs(df['accel_x']) > 8) |  # Hard braking/acceleration
            (np.abs(df['accel_y']) > 6) |  # Sharp turns
            (np.abs(df['jerk']) > 5) |     # Sudden changes
            (df['lateral_accel'] > 8) |    # High lateral forces
            ((df['speed_kmph'] > 100) & (df['lateral_accel'] > 4)) |  # High speed cornering
            ((df['brake_position'] > 80) & (df['speed_kmph'] > 60))   # Hard braking at speed
        )
        
        # Add some noise to make it more realistic
        noise = np.random.random(n_samples) < 0.1  # 10% noise
        df['harsh_driving'] = (harsh_conditions | noise) & ~(~harsh_conditions & noise)
        
        # Balance the dataset somewhat
        harsh_ratio = df['harsh_driving'].mean()
        if harsh_ratio < 0.2:  # If less than 20% harsh driving, add more
            additional_harsh = np.random.choice(
                df[~df['harsh_driving']].index, 
                size=int(0.15 * n_samples), 
                replace=False
            )
            df.loc[additional_harsh, 'harsh_driving'] = True
        
        logger.info(f"Generated {n_samples} samples with {df['harsh_driving'].sum()} harsh driving instances ({df['harsh_driving'].mean():.2%})")
        
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> tuple:
        """Prepare features and target for training"""
        feature_columns = [
            'speed_kmph', 'accel_x', 'accel_y', 'accel_z', 'jerk', 'yaw_rate',
            'heading_change', 'throttle_position', 'brake_position',
            'accel_magnitude', 'lateral_accel', 'speed_accel_ratio', 'brake_accel_correlation'
        ]
        
        X = df[feature_columns].copy()
        y = df['harsh_driving'].astype(int)
        
        self.feature_names = feature_columns
        
        return X, y
    
    def train_model(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """Train the harsh driving detection model"""
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train RandomForest model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )
        
        logger.info("Training RandomForest model...")
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5)
        
        # Predictions for detailed metrics
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        # Calculate metrics
        auc_score = roc_auc_score(y_test, y_pred_proba)
        
        # Feature importance
        feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
        
        # Store metadata
        self.model_metadata = {
            'model_version': self.model_version,
            'model_type': 'RandomForestClassifier',
            'training_date': datetime.now().isoformat(),
            'feature_names': self.feature_names,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'train_accuracy': float(train_score),
            'test_accuracy': float(test_score),
            'cv_mean_accuracy': float(cv_scores.mean()),
            'cv_std_accuracy': float(cv_scores.std()),
            'auc_score': float(auc_score),
            'feature_importance': {k: float(v) for k, v in feature_importance.items()},
            'hyperparameters': {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'class_weight': 'balanced'
            }
        }
        
        # Print results
        logger.info(f"Training completed:")
        logger.info(f"  Train Accuracy: {train_score:.3f}")
        logger.info(f"  Test Accuracy: {test_score:.3f}")
        logger.info(f"  CV Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        logger.info(f"  AUC Score: {auc_score:.3f}")
        
        logger.info("\nClassification Report:")
        logger.info(classification_report(y_test, y_pred))
        
        logger.info("\nTop 5 Feature Importances:")
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        for feature, importance in sorted_features[:5]:
            logger.info(f"  {feature}: {importance:.3f}")
        
        return self.model_metadata
    
    def save_model(self, models_dir: str = None) -> str:
        """Save the trained model and metadata"""
        if not models_dir:
            models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        
        os.makedirs(models_dir, exist_ok=True)
        
        # Create model bundle
        model_bundle = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'metadata': self.model_metadata
        }
        
        # Save with version and as latest
        version_path = os.path.join(models_dir, f'harsh_driving_model_{self.model_version}.pkl')
        latest_path = os.path.join(models_dir, 'harsh_driving_model_latest.pkl')
        metadata_path = os.path.join(models_dir, f'harsh_driving_metadata_{self.model_version}.json')
        latest_metadata_path = os.path.join(models_dir, 'harsh_driving_metadata_latest.json')
        
        # Save model bundle
        joblib.dump(model_bundle, version_path)
        joblib.dump(model_bundle, latest_path)
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(self.model_metadata, f, indent=2)
        
        with open(latest_metadata_path, 'w') as f:
            json.dump(self.model_metadata, f, indent=2)
        
        logger.info(f"Model saved:")
        logger.info(f"  Version: {version_path}")
        logger.info(f"  Latest: {latest_path}")
        logger.info(f"  Metadata: {metadata_path}")
        
        return version_path
    
    def load_and_test_model(self, model_path: str) -> dict:
        """Load and test the saved model"""
        logger.info(f"Loading model from {model_path}")
        
        model_bundle = joblib.load(model_path)
        model = model_bundle['model']
        scaler = model_bundle['scaler']
        feature_names = model_bundle['feature_names']
        
        # Generate test data
        test_data = self.generate_synthetic_data(1000)
        X_test, y_test = self.prepare_features(test_data)
        X_test_scaled = scaler.transform(X_test)
        
        # Test predictions
        predictions = model.predict(X_test_scaled)
        probabilities = model.predict_proba(X_test_scaled)
        
        accuracy = model.score(X_test_scaled, y_test)
        
        logger.info(f"Model test completed:")
        logger.info(f"  Test Accuracy: {accuracy:.3f}")
        logger.info(f"  Predictions shape: {predictions.shape}")
        logger.info(f"  Probabilities shape: {probabilities.shape}")
        
        return {
            'test_accuracy': accuracy,
            'predictions_count': len(predictions),
            'harsh_driving_detected': int(predictions.sum()),
            'model_loaded_successfully': True
        }

def main():
    """Main training function"""
    logger.info("Starting harsh driving model training...")
    
    # Initialize trainer
    trainer = HarshDrivingModelTrainer()
    
    # Generate training data
    logger.info("Generating synthetic training data...")
    training_data = trainer.generate_synthetic_data(n_samples=15000)
    
    # Prepare features
    X, y = trainer.prepare_features(training_data)
    
    # Train model
    metadata = trainer.train_model(X, y)
    
    # Save model
    model_path = trainer.save_model()
    
    # Test saved model
    test_results = trainer.load_and_test_model(model_path)
    
    logger.info("Training pipeline completed successfully!")
    
    return {
        'model_path': model_path,
        'metadata': metadata,
        'test_results': test_results
    }

if __name__ == "__main__":
    results = main()