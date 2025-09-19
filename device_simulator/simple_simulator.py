import time
import requests
import random
import uuid
import argparse
from datetime import datetime

API_URL = "http://localhost:5000/driver_score"

def generate_event(device_id):
    speed = max(0, random.gauss(50, 15))
    accel_x = random.gauss(0, 1.5)
    accel_y = random.gauss(0, 1.0)
    accel_z = random.gauss(9.8, 0.3)
    jerk = random.gauss(0, 0.3)
    yaw = random.gauss(0, 0.1)
    return {
        "device_id": device_id,
        "timestamp": int(time.time()),
        "speed": round(speed, 2),
        "accel_x": round(accel_x, 3),
        "accel_y": round(accel_y, 3),
        "accel_z": round(accel_z, 3),
        "jerk": round(jerk, 4),
        "yaw": round(yaw, 4)
    }

def run_simulator(device_count=3, interval=1.0):
    device_ids = [str(uuid.uuid4())[:8] for _ in range(device_count)]
    print("Simulating devices:", device_ids)
    while True:
        for dev in device_ids:
            ev = generate_event(dev)
            try:
                r = requests.post(API_URL, json=ev, timeout=5)
                if r.ok:
                    data = r.json()
                    print(f"{datetime.now().isoformat()} | {dev} -> score={data.get('driver_score'):.2f} model={data.get('model')}")
                else:
                    print("Bad response:", r.status_code, r.text)
            except Exception as e:
                print("Failed to send:", e)
        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", type=int, default=3)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    run_simulator(device_count=args.devices, interval=args.interval)