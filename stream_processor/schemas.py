#!/usr/bin/env python3
"""
Pydantic models for telemetry payload validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import re

class LocationModel(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")

class AccelerationModel(BaseModel):
    x: float = Field(..., description="X-axis acceleration (m/s²)")
    y: float = Field(..., description="Y-axis acceleration (m/s²)")
    z: float = Field(..., description="Z-axis acceleration (m/s²)")

class EngineDataModel(BaseModel):
    rpm: Optional[float] = Field(None, ge=0, le=10000)
    fuelLevel: Optional[float] = Field(None, ge=0, le=100)
    engineTemp: Optional[float] = Field(None, ge=-40, le=150)

class DiagnosticsModel(BaseModel):
    errorCodes: Optional[List[str]] = Field(default_factory=list)
    batteryVoltage: Optional[float] = Field(None, ge=0, le=24)

class TelemetryModel(BaseModel):
    deviceId: str = Field(..., regex=r"^[A-Z0-9_]{8,32}$", description="Unique device identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    location: LocationModel
    speedKmph: float = Field(..., ge=0, le=300, description="Speed in kilometers per hour")
    heading: Optional[float] = Field(None, ge=0, le=360, description="Heading in degrees")
    acceleration: Optional[AccelerationModel] = None
    engineData: Optional[EngineDataModel] = None
    diagnostics: Optional[DiagnosticsModel] = None

    @validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('Invalid timestamp format')

class EventModel(BaseModel):
    deviceId: str = Field(..., regex=r"^[A-Z0-9_]{8,32}$")
    eventType: str = Field(..., description="Event type")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    location: Optional[LocationModel] = None
    speedBefore: Optional[float] = Field(None, ge=0)
    speedAfter: Optional[float] = Field(None, ge=0)
    accelPeak: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('Invalid timestamp format')

class V2XModel(BaseModel):
    deviceId: str = Field(..., regex=r"^[A-Z0-9_]{8,32}$")
    type: str = Field(..., description="V2X message type")
    pos: LocationModel
    ttl_seconds: Optional[int] = Field(5, ge=1, le=300)
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)