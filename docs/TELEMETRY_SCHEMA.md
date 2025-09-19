# Telemetry Schema

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| device_id | string | Unique OBU device identifier |
| timestamp | integer | Unix timestamp |
| speed | number | Vehicle speed in km/h |
| accel_x | number | Longitudinal acceleration (m/s²) |
| accel_y | number | Lateral acceleration (m/s²) |
| accel_z | number | Vertical acceleration (m/s²) |
| jerk | number | Rate of acceleration change (m/s³) |
| yaw | number | Yaw rate (rad/s) |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| latitude | number | GPS latitude |
| longitude | number | GPS longitude |
| altitude | number | GPS altitude |

## Example Payload

```json
{
  "device_id": "OBU-12345678",
  "timestamp": 1703123456,
  "speed": 65.2,
  "accel_x": -2.1,
  "accel_y": 0.3,
  "accel_z": 9.8,
  "jerk": 0.5,
  "yaw": 0.02,
  "latitude": 20.2961,
  "longitude": 85.8245,
  "altitude": 25.0
}
```