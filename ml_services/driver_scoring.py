#!/usr/bin/env python3
"""
ML Services - Driver Scoring Model
Real-time driver behavior analysis and scoring
"""

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriverScoringModel:
    def __init__(self, db_config):
        self.db_config = db_config
        self.event_classifier = None
        self.score_regressor = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'speed_mean', 'speed_std', 'speed_max',
            'accel_x_mean', 'accel_x_std', 'accel_x_min', 'accel_x_max',
            'accel_y_mean', 'accel_y_std',
            'gyro_x_std', 'gyro_y_std',
            'rpm_mean', 'rpm_std',
            'throttle_mean', 'throttle_std', 'throttle_max',
            'brake_mean', 'brake_std', 'brake_max',
            'jerk_mean', 'jerk_std',
            'harsh_events_count',
            'time_of_day', 'day_of_week'
        ]
        
    def extract_features(self, telemetry_window):
        """Extract features from telemetry time window"""
        if not telemetry_window:
            return None
        
        df = pd.DataFrame(telemetry_window)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Basic statistics
        features = {
            'speed_mean': df['speed_kmph'].mean(),
            'speed_std': df['speed_kmph'].std(),
            'speed_max': df['speed_kmph'].max(),
            
            'accel_x_mean': df['acceleration_x'].mean(),
            'accel_x_std': df['acceleration_x'].std(),
            'accel_x_min': df['acceleration_x'].min(),
            'accel_x_max': df['acceleration_x'].max(),
            
            'accel_y_mean': df['acceleration_y'].mean(),
            'accel_y_std': df['acceleration_y'].std(),
            
            'gyro_x_std': df['gyro_x'].std(),
            'gyro_y_std': df['gyro_y'].std(),
            
            'rpm_mean': df['rpm'].mean(),
            'rpm_std': df['rpm'].std(),
            
            'throttle_mean': df['throttle'].mean(),
            'throttle_std': df['throttle'].std(),
            'throttle_max': df['throttle'].max(),
            
            'brake_mean': df['brake'].mean(),
            'brake_std': df['brake'].std(),
            'brake_max': df['brake'].max(),
        }
        
        # Calculate jerk (rate of change of acceleration)
        df['jerk'] = df['acceleration_x'].diff() / df['timestamp'].diff().dt.total_seconds()
        features['jerk_mean'] = df['jerk'].mean()
        features['jerk_std'] = df['jerk'].std()
        
        # Count harsh events
        features['harsh_events_count'] = len(df[
            (df['acceleration_x'] < -5) | (df['acceleration_x'] > 5)
        ])
        
        # Time-based features
        first_timestamp = df['timestamp'].iloc[0]
        features['time_of_day'] = first_timestamp.hour + first_timestamp.minute / 60.0
        features['day_of_week'] = first_timestamp.weekday()
        
        # Fill NaN values
        for key, value in features.items():
            if pd.isna(value):
                features[key] = 0.0
        
        return features
    
    def generate_synthetic_training_data(self, n_samples=10000):
        """Generate synthetic training data for model development"""
        logger.info("Generating synthetic training data...")
        
        np.random.seed(42)
        data = []
        
        for i in range(n_samples):
            # Generate different driver profiles
            driver_type = np.random.choice(['safe', 'aggressive', 'normal'], p=[0.3, 0.2, 0.5])
            
            if driver_type == 'safe':
                speed_mean = np.random.normal(45, 10)
                accel_x_std = np.random.normal(0.5, 0.2)
                harsh_events = np.random.poisson(0.1)
                score = np.random.normal(85, 10)
            elif driver_type == 'aggressive':
                speed_mean = np.random.normal(70, 15)
                accel_x_std = np.random.normal(2.0, 0.5)
                harsh_events = np.random.poisson(2.0)
                score = np.random.normal(35, 15)
            else:  # normal
                speed_mean = np.random.normal(55, 12)
                accel_x_std = np.random.normal(1.0, 0.3)
                harsh_events = np.random.poisson(0.5)
                score = np.random.normal(65, 15)
            
            # Clamp values
            speed_mean = max(0, min(120, speed_mean))
            score = max(0, min(100, score))
            
            features = {
                'speed_mean': speed_mean,
                'speed_std': max(0, np.random.normal(8, 3)),
                'speed_max': speed_mean + np.random.normal(20, 10),
                
                'accel_x_mean': np.random.normal(0, 0.2),
                'accel_x_std': max(0, accel_x_std),
                'accel_x_min': np.random.normal(-3, 1),
                'accel_x_max': np.random.normal(3, 1),
                
                'accel_y_mean': np.random.normal(0, 0.1),
                'accel_y_std': max(0, np.random.normal(0.3, 0.1)),
                
                'gyro_x_std': max(0, np.random.normal(0.01, 0.005)),
                'gyro_y_std': max(0, np.random.normal(0.01, 0.005)),
                
                'rpm_mean': speed_mean * 30 + np.random.normal(800, 200),
                'rpm_std': max(0, np.random.normal(300, 100)),
                
                'throttle_mean': max(0, np.random.normal(25, 15)),
                'throttle_std': max(0, np.random.normal(15, 5)),
                'throttle_max': max(0, np.random.normal(80, 20)),
                
                'brake_mean': max(0, np.random.normal(5, 10)),
                'brake_std': max(0, np.random.normal(8, 5)),
                'brake_max': max(0, np.random.normal(30, 20)),
                
                'jerk_mean': np.random.normal(0, 0.5),
                'jerk_std': max(0, np.random.normal(1.0, 0.3)),
                
                'harsh_events_count': harsh_events,
                
                'time_of_day': np.random.uniform(0, 24),
                'day_of_week': np.random.randint(0, 7),
                
                'score': score,
                'has_harsh_event': harsh_events > 0
            }
            
            data.append(features)
        
        return pd.DataFrame(data)
    
    def train_models(self):
        """Train both event classifier and score regressor"""
        logger.info("Training driver scoring models...")
        
        # Generate training data
        df = self.generate_synthetic_training_data()
        
        # Prepare features
        X = df[self.feature_columns]
        y_events = df['has_harsh_event']
        y_score = df['score']
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_events_train, y_events_test, y_score_train, y_score_test = train_test_split(
            X_scaled, y_events, y_score, test_size=0.2, random_state=42
        )
        
        # Train event classifier
        self.event_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.event_classifier.fit(X_train, y_events_train)
        
        # Train score regressor
        self.score_regressor = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.score_regressor.fit(X_train, y_score_train)
        
        # Evaluate models
        event_accuracy = self.event_classifier.score(X_test, y_events_test)
        score_r2 = self.score_regressor.score(X_test, y_score_test)
        
        logger.info(f"✓ Event classifier accuracy: {event_accuracy:.3f}")
        logger.info(f"✓ Score regressor R²: {score_r2:.3f}")
        
        # Save models
        self.save_models()
    
    def save_models(self):
        """Save trained models to disk"""
        joblib.dump(self.event_classifier, 'models/event_classifier.pkl')
        joblib.dump(self.score_regressor, 'models/score_regressor.pkl')
        joblib.dump(self.scaler, 'models/scaler.pkl')
        logger.info("✓ Models saved")
    
    def load_models(self):
        """Load trained models from disk"""
        try:
            self.event_classifier = joblib.load('models/event_classifier.pkl')
            self.score_regressor = joblib.load('models/score_regressor.pkl')
            self.scaler = joblib.load('models/scaler.pkl')
            logger.info("✓ Models loaded")
            return True
        except FileNotFoundError:
            logger.warning("Models not found, training new ones...")
            return False
    
    def predict_driver_score(self, telemetry_window):
        """Predict driver score from telemetry window"""
        if not self.event_classifier or not self.score_regressor:
            if not self.load_models():
                self.train_models()
        
        # Extract features
        features = self.extract_features(telemetry_window)
        if not features:
            return None
        
        # Prepare feature vector
        feature_vector = np.array([[features[col] for col in self.feature_columns]])
        feature_vector_scaled = self.scaler.transform(feature_vector)
        
        # Predict
        event_probability = self.event_classifier.predict_proba(feature_vector_scaled)[0][1]
        base_score = self.score_regressor.predict(feature_vector_scaled)[0]
        
        # Adjust score based on event probability
        adjusted_score = base_score * (1 - event_probability * 0.3)
        adjusted_score = max(0, min(100, adjusted_score))
        
        # Detect specific events
        events = []
        if features['accel_x_min'] < -5:
            events.append('HARSH_BRAKE')
        if features['accel_x_max'] > 5:
            events.append('HARSH_ACCEL')
        if features['speed_max'] > 80:
            events.append('OVER_SPEED')
        
        return {
            'score': round(adjusted_score, 1),
            'event_probability': round(event_probability, 3),
            'events': events,
            'features': features,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    def get_telemetry_window(self, device_id, window_minutes=10):
        """Get telemetry data for the last N minutes"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT * FROM telemetry 
            WHERE device_id = %s 
            AND time >= NOW() - INTERVAL '%s minutes'
            ORDER BY time DESC
            """
            
            cursor.execute(query, (device_id, window_minutes))
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            return []
    
    def score_device(self, device_id):
        """Score a specific device based on recent telemetry"""
        telemetry = self.get_telemetry_window(device_id)
        
        if not telemetry:
            return {
                'error': 'No telemetry data available',
                'device_id': device_id
            }
        
        result = self.predict_driver_score(telemetry)
        if result:
            result['device_id'] = device_id
            result['telemetry_points'] = len(telemetry)
        
        return result

# Flask API for ML services
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Initialize model
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'transport_system',
    'user': 'admin',
    'password': 'password'
}

scorer = DriverScoringModel(db_config)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'driver_scoring'})

@app.route('/score', methods=['POST'])
def score_telemetry():
    """Score driver based on telemetry window"""
    try:
        data = request.get_json()
        telemetry_window = data.get('telemetry', [])
        
        if not telemetry_window:
            return jsonify({'error': 'No telemetry data provided'}), 400
        
        result = scorer.predict_driver_score(telemetry_window)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': 'Failed to process telemetry'}), 500
            
    except Exception as e:
        logger.error(f"Scoring error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/score/<device_id>', methods=['GET'])
def score_device(device_id):
    """Get latest score for a device"""
    try:
        result = scorer.score_device(device_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Device scoring error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/train', methods=['POST'])
def train_models():
    """Retrain models"""
    try:
        scorer.train_models()
        return jsonify({'status': 'Models trained successfully'})
    except Exception as e:
        logger.error(f"Training error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    import os
    os.makedirs('models', exist_ok=True)
    
    # Train models if they don't exist
    if not scorer.load_models():
        scorer.train_models()
    
    app.run(host='0.0.0.0', port=5001, debug=True)