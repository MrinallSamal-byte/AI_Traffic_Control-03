#!/usr/bin/env python3
"""
ML Model Manager - Handles model versioning, drift detection, and ensemble models
"""

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import mlflow
import mlflow.sklearn
from datetime import datetime, timedelta
import logging
from scipy import stats
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, model_registry_uri="sqlite:///mlflow.db"):
        self.model_registry_uri = model_registry_uri
        mlflow.set_tracking_uri(model_registry_uri)
        
        self.models = {}
        self.scalers = {}
        self.reference_data = None
        self.drift_threshold = 0.1
        
    def register_model(self, model_name, model, scaler=None, version="1.0"):
        """Register model with MLflow"""
        with mlflow.start_run():
            mlflow.sklearn.log_model(model, model_name)
            mlflow.log_param("version", version)
            mlflow.log_param("model_type", type(model).__name__)
            
            if scaler:
                mlflow.sklearn.log_model(scaler, f"{model_name}_scaler")
            
            # Register in MLflow Model Registry
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/{model_name}"
            mlflow.register_model(model_uri, model_name)
            
        self.models[model_name] = model
        if scaler:
            self.scalers[model_name] = scaler
            
        logger.info(f"Registered model {model_name} version {version}")
    
    def load_model(self, model_name, version="latest"):
        """Load model from MLflow registry"""
        try:
            if version == "latest":
                model_version = mlflow.MlflowClient().get_latest_versions(
                    model_name, stages=["Production", "Staging"]
                )[0].version
            else:
                model_version = version
            
            model_uri = f"models:/{model_name}/{model_version}"
            model = mlflow.sklearn.load_model(model_uri)
            
            # Try to load scaler
            try:
                scaler_uri = f"models:/{model_name}_scaler/{model_version}"
                scaler = mlflow.sklearn.load_model(scaler_uri)
                self.scalers[model_name] = scaler
            except:
                logger.warning(f"No scaler found for {model_name}")
            
            self.models[model_name] = model
            logger.info(f"Loaded model {model_name} version {model_version}")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
    
    def detect_drift(self, new_data, reference_data=None, method="psi"):
        """Detect data drift using PSI or KL divergence"""
        if reference_data is None:
            reference_data = self.reference_data
            
        if reference_data is None:
            logger.warning("No reference data available for drift detection")
            return {"drift_detected": False, "drift_score": 0.0}
        
        drift_scores = {}
        
        for column in new_data.columns:
            if column in reference_data.columns:
                if method == "psi":
                    score = self._calculate_psi(reference_data[column], new_data[column])
                elif method == "ks":
                    score = stats.ks_2samp(reference_data[column], new_data[column]).statistic
                else:
                    score = 0.0
                
                drift_scores[column] = score
        
        avg_drift_score = np.mean(list(drift_scores.values()))
        drift_detected = avg_drift_score > self.drift_threshold
        
        return {
            "drift_detected": drift_detected,
            "drift_score": avg_drift_score,
            "feature_scores": drift_scores,
            "threshold": self.drift_threshold
        }
    
    def _calculate_psi(self, reference, current, bins=10):
        """Calculate Population Stability Index (PSI)"""
        try:
            # Create bins based on reference data
            _, bin_edges = np.histogram(reference, bins=bins)
            
            # Calculate distributions
            ref_counts, _ = np.histogram(reference, bins=bin_edges)
            cur_counts, _ = np.histogram(current, bins=bin_edges)
            
            # Normalize to get percentages
            ref_pct = ref_counts / len(reference)
            cur_pct = cur_counts / len(current)
            
            # Avoid division by zero
            ref_pct = np.where(ref_pct == 0, 0.0001, ref_pct)
            cur_pct = np.where(cur_pct == 0, 0.0001, cur_pct)
            
            # Calculate PSI
            psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
            
            return psi
            
        except Exception as e:
            logger.error(f"PSI calculation error: {e}")
            return 0.0
    
    def create_ensemble_model(self, models, weights=None):
        """Create ensemble model combining multiple models"""
        if weights is None:
            weights = [1.0 / len(models)] * len(models)
        
        class EnsembleModel:
            def __init__(self, models, weights):
                self.models = models
                self.weights = weights
            
            def predict(self, X):
                predictions = []
                for model in self.models:
                    pred = model.predict(X)
                    predictions.append(pred)
                
                # Weighted average
                ensemble_pred = np.average(predictions, axis=0, weights=self.weights)
                return ensemble_pred
            
            def predict_with_confidence(self, X):
                predictions = []
                for model in self.models:
                    pred = model.predict(X)
                    predictions.append(pred)
                
                predictions = np.array(predictions)
                ensemble_pred = np.average(predictions, axis=0, weights=self.weights)
                
                # Calculate confidence as inverse of prediction variance
                pred_std = np.std(predictions, axis=0)
                confidence = 1.0 / (1.0 + pred_std)
                
                return ensemble_pred, confidence
        
        return EnsembleModel(models, weights)
    
    def update_reference_data(self, data):
        """Update reference data for drift detection"""
        self.reference_data = data.copy()
        logger.info(f"Updated reference data with {len(data)} samples")

class DriverScoringEnsemble:
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.rf_model = None
        self.lstm_model = None
        self.ensemble_model = None
        
    def train_random_forest(self, X_train, y_train):
        """Train Random Forest model"""
        self.rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_train)
        
        self.rf_model.fit(X_scaled, y_train)
        
        # Register with model manager
        self.model_manager.register_model(
            "driver_scoring_rf", 
            self.rf_model, 
            scaler, 
            version="1.0"
        )
        
        logger.info("Random Forest model trained and registered")
    
    def create_lstm_model(self, sequence_length=10, features=5):
        """Create LSTM model (placeholder - requires TensorFlow)"""
        # This would require TensorFlow/Keras
        # For now, return a mock model
        class MockLSTM:
            def predict(self, X):
                return np.random.uniform(0.3, 0.9, len(X))
        
        self.lstm_model = MockLSTM()
        logger.info("LSTM model created (mock implementation)")
    
    def create_ensemble(self):
        """Create ensemble of RF and LSTM models"""
        if self.rf_model and self.lstm_model:
            models = [self.rf_model, self.lstm_model]
            weights = [0.7, 0.3]  # RF gets more weight
            
            self.ensemble_model = self.model_manager.create_ensemble_model(models, weights)
            logger.info("Ensemble model created")
    
    def predict_with_confidence(self, features):
        """Predict driver score with confidence"""
        if self.ensemble_model:
            score, confidence = self.ensemble_model.predict_with_confidence(features)
            return {
                "driver_score": float(score[0]),
                "confidence": float(confidence[0]),
                "model_type": "ensemble"
            }
        elif self.rf_model:
            scaler = self.model_manager.scalers.get("driver_scoring_rf")
            if scaler:
                features_scaled = scaler.transform(features)
                score = self.rf_model.predict(features_scaled)
                return {
                    "driver_score": float(score[0]),
                    "confidence": 0.8,  # Default confidence for single model
                    "model_type": "random_forest"
                }
        
        return {
            "driver_score": 0.5,
            "confidence": 0.1,
            "model_type": "fallback"
        }

def main():
    """Example usage"""
    model_manager = ModelManager()
    
    # Create sample training data
    np.random.seed(42)
    X_train = np.random.randn(1000, 5)
    y_train = np.random.uniform(0.2, 0.9, 1000)
    
    # Train ensemble model
    ensemble = DriverScoringEnsemble(model_manager)
    ensemble.train_random_forest(X_train, y_train)
    ensemble.create_lstm_model()
    ensemble.create_ensemble()
    
    # Test prediction
    test_features = np.random.randn(1, 5)
    result = ensemble.predict_with_confidence(test_features)
    print(f"Prediction result: {result}")
    
    # Test drift detection
    new_data = pd.DataFrame(np.random.randn(100, 5))
    reference_data = pd.DataFrame(X_train)
    
    drift_result = model_manager.detect_drift(new_data, reference_data)
    print(f"Drift detection result: {drift_result}")

if __name__ == "__main__":
    main()