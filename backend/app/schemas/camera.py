from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.core.constants import CameraStatus, CameraSourceType

class CameraBase(BaseModel):
    name: str = Field(..., examples=["Northern Fence Line"])
    sector_zone: str = Field(default="Sector 1", examples=["Sector 1"])
    source_type: CameraSourceType = Field(default=CameraSourceType.RTSP, examples=[CameraSourceType.RTSP])
    stream_url: str = Field(..., examples=["rtsp://admin:pass@192.168.1.101:554/stream1"])
    rtsp_transport: str = Field(default="tcp", examples=["tcp"])
    fps: float = Field(default=25.0, examples=[25.0])
    resolution: str = Field(default="1080x720", examples=["1080x720"])
    ai_pipeline: str = Field(default="ByteTrack + FRS + ANPR + DQN", examples=["ByteTrack + FRS + ANPR + DQN"])

class CameraCreate(CameraBase):
    id: str = Field(..., examples=["CAM-01"])

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    sector_zone: Optional[str] = None
    stream_url: Optional[str] = None
    status: Optional[CameraStatus] = None
    is_active: Optional[bool] = None

class CameraResponse(CameraBase):
    id: str
    status: CameraStatus
    is_active: bool
    last_heartbeat_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
