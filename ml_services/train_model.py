import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib
import os

OUT_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

def generate_synthetic_data(n=5000, random_state=42):
    """Generate synthetic telemetry data for training"""
    rng = np.random.RandomState(random_state)
    speed = rng.normal(loc=50, scale=15, size=n).clip(0, 160)
    accel_x = rng.normal(loc=0, scale=1.5, size=n)
    accel_y = rng.normal(loc=0, scale=1.0, size=n)
    accel_z = rng.normal(loc=9.8, scale=0.3, size=n)
    jerk = rng.normal(loc=0, scale=0.5, size=n)
    yaw = rng.normal(loc=0, scale=0.2, size=n)

    # Calculate risk score based on driving behavior
    risk = (
        0.02 * speed +
        7.0 * np.abs(accel_x) +
        4.0 * np.abs(accel_y) +
        6.0 * np.abs(jerk) +
        10.0 * (speed > 100).astype(float) +
        rng.normal(0, 5, size=n)
    )
    risk = np.clip(100 * (risk - risk.min()) / (risk.max() - risk.min() + 1e-9), 0, 100)
    
    df = pd.DataFrame({
        "speed": speed,
        "accel_x": accel_x,
        "accel_y": accel_y,
        "accel_z": accel_z,
        "jerk": jerk,
        "yaw": yaw,
        "risk": risk
    })
    return df

def train_and_save_model(out_path=OUT_PATH):
    """Train RandomForest model and save to disk"""
    print("Generating synthetic training data...")
    df = generate_synthetic_data()
    X = df[["speed", "accel_x", "accel_y", "accel_z", "jerk", "yaw"]]
    y = df["risk"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training RandomForest model...")
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X_train, y_train)
    
    train_r2 = model.score(X_train, y_train)
    test_r2 = model.score(X_test, y_test)
    print(f"Train R²: {train_r2:.4f}")
    print(f"Test R²: {test_r2:.4f}")
    
    joblib.dump(model, out_path)
    print(f"Model saved to {out_path}")
    return train_r2, test_r2

if __name__ == "__main__":
    train_and_save_model()