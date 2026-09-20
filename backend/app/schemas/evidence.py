from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)

class EvidenceVerifyResult(BaseModel):
    is_valid: bool
    computed_hash: str
    expected_hash: str
    file_path: str
    message: str
