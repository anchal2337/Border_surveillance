from datetime import datetime, timezone
from typing import Optional, Dict
from pydantic import BaseModel, Field


class TelemetrySnapshot(BaseModel):
    camera_id: str
    fps: float
    active_tracks: int
    max_threat: int
    engine_mode: str
    model_confidences: Dict[str, float] = Field(default_factory=lambda: {
        "object_detection": 0.94,
        "tactical_threat": 0.96,
        "face_recognition": 0.92,
        "plate_ocr": 0.95,
    })
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
