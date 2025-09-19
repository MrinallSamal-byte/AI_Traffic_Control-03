"""Pydantic models for API request/response validation."""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime


class UserRegistration(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    @validator('password')
    def password_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Password cannot be empty')
        return v


class DeviceRegistration(BaseModel):
    registration_no: str
    obu_device_id: str
    
    @validator('registration_no')
    def validate_registration_no(cls, v):
        if not v.strip():
            raise ValueError('Registration number cannot be empty')
        return v.strip().upper()
    
    @validator('obu_device_id')
    def validate_device_id(cls, v):
        if not v.strip():
            raise ValueError('Device ID cannot be empty')
        return v.strip()


class TelemetryData(BaseModel):
    deviceId: str
    timestamp: str
    location: Dict[str, float]
    speedKmph: float
    heading: Optional[float] = None
    acceleration: Optional[Dict[str, float]] = None
    
    @validator('location')
    def validate_location(cls, v):
        if 'lat' not in v or 'lon' not in v:
            raise ValueError('Location must contain lat and lon')
        if not (-90 <= v['lat'] <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        if not (-180 <= v['lon'] <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v
    
    @validator('speedKmph')
    def validate_speed(cls, v):
        if v < 0 or v > 300:
            raise ValueError('Speed must be between 0 and 300 km/h')
        return v


class TollCharge(BaseModel):
    vehicleId: str
    gantryId: str
    calculatedPrice: float
    
    @validator('calculatedPrice')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return round(v, 2)