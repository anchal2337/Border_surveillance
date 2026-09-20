from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from backend.app.core.constants import EvidenceStatus, SeverityLevel

class EvidenceStatusUpdate(BaseModel):
    status: EvidenceStatus = Field(..., examples=[EvidenceStatus.INVESTIGATING])
    resolution_notes: Optional[str] = Field(None, examples=["Case forwarded to Battalion Commander for review."])

class EvidenceResponse(BaseModel):
    id: str
    camera_id: Optional[str] = None
    track_session_id: Optional[int] = None
    event: str
    camera_name: str
    location: str
    track_id: int
    object_label: str
    class_name: str
    severity: SeverityLevel
    threat_score: int
    behavior: str
    identity: Optional[str] = None
    speed_px_sec: float
    dwell_sec: float
    crop_image: str
    scene_image: str
    sha256_hash: str
    status: EvidenceStatus
    details: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

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

class EvidenceVerifyResult(BaseModel):
    is_valid: bool
    computed_hash: str
    expected_hash: str
    file_path: str
    message: str
