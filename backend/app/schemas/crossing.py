from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class VehicleCrossingResponse(BaseModel):
    id: int
    camera_id: Optional[str] = None
    track_id: int
    license_plate: Optional[str] = None
    ocr_confidence: float
    vehicle_type: str
    is_whitelisted: bool
    crossing_type: str
    image_path: str
    source_file: Optional[str] = None
    details: Optional[str] = None
    crossed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VehicleCrossingSummary(BaseModel):
    total_crossings: int
    whitelisted_count: int
    unregistered_count: int
    latest_crossing_time: Optional[str] = None
