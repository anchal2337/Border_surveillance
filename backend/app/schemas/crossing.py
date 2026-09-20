from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


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

    @field_validator("track_id", mode="before")
    @classmethod
    def parse_track_id(cls, v):
        if isinstance(v, bytes):
            import struct
            try:
                if len(v) == 8:
                    return struct.unpack("<q", v)[0]
                elif len(v) == 4:
                    return struct.unpack("<i", v)[0]
                return int.from_bytes(v, "little")
            except Exception:
                return 0
        try:
            return int(v)
        except Exception:
            return 0

    model_config = ConfigDict(from_attributes=True)


class VehicleCrossingSummary(BaseModel):
    total_crossings: int
    whitelisted_count: int
    unregistered_count: int
    latest_crossing_time: Optional[str] = None
