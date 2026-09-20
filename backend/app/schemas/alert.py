from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.core.constants import SeverityLevel

class AlertAcknowledge(BaseModel):
    resolution_notes: Optional[str] = Field(None, examples=["False alarm: authorized military patrol confirmed by radio."])

class AlertResponse(BaseModel):
    id: str
    camera_id: str
    track_session_id: Optional[int] = None
    alert_type: str
    severity: SeverityLevel
    threat_score: int
    behavior: str
    label: str
    details: Optional[str] = None
    snapshot_url: Optional[str] = None
    is_acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
