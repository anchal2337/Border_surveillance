from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.core.constants import ZoneType

class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, examples=["Perimeter Sector 4"])
    zone_type: ZoneType = Field(default=ZoneType.GEOFENCE)
    coordinates: List[List[int]] = Field(..., examples=[[[162, 252], [918, 252], [1026, 612], [54, 612]]])
    alert_on_entry: bool = Field(default=True)
    alert_on_exit: bool = Field(default=False)
    sensitivity: float = Field(default=1.0)
    is_active: bool = Field(default=True)

class ZoneCreate(ZoneUpdate):
    camera_id: str = Field(..., examples=["CAM-01"])

class ZoneResponse(BaseModel):
    id: str
    camera_id: str
    name: str
    zone_type: ZoneType
    coordinates: str  # Stored as JSON string in SQLite
    alert_on_entry: bool
    alert_on_exit: bool
    sensitivity: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DynamicZoneCalibrationPayload(BaseModel):
    """Payload sent from HTML5 Canvas Zone Studio in sentry dashboard."""
    camera_id: str = Field(..., examples=["CAM-01"])
    geofence: Optional[List[List[int]]] = Field(None, examples=[[[162, 252], [918, 252], [1026, 612], [54, 612]]])
    tripwire: Optional[List[List[int]]] = Field(None, examples=[[[108, 468], [972, 468]]])
