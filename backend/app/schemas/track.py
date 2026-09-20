from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict


class ActiveTrackInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    track_id: int
    camera_id: str
    class_name: str = "person"
    threat_score: int = 0
    behavior: str = "Normal"
    identity: Optional[str] = None
    is_authorized: Optional[bool] = None
    speed_px_sec: float = 0.0
    dwell_sec: float = 0.0
    last_position: Optional[List[int]] = None


class TrackSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: str
    track_number: int
    class_name: str
    first_seen_at: datetime
    last_seen_at: datetime
    max_threat_score: int
    dominant_behavior: str
    resolved_identity: Optional[str] = None
    is_authorized: Optional[bool] = None
    current_speed_px_sec: float
    total_dwell_sec: float
    trajectory_points: str
    created_at: datetime
