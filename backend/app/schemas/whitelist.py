from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

# -----------------------------------------------------------------------------
# Biometric Personnel (FRS) Schemas
# -----------------------------------------------------------------------------
class FaceEnrollRequest(BaseModel):
    full_name: str = Field(..., examples=["Captain Vikram Rathore"])
    designation: str = Field(default="Border Guard", examples=["Border Guard"])
    badge_number: Optional[str] = Field(None, examples=["BG-804"])
    department: str = Field(default="Perimeter Sentry", examples=["Perimeter Sentry"])
    face_embedding: List[float] = Field(..., description="512-float biometric embedding vector")
    photo_path: Optional[str] = None

class PersonnelResponse(BaseModel):
    id: str
    full_name: str
    designation: str
    badge_number: Optional[str] = None
    department: str
    photo_path: Optional[str] = None
    is_authorized: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# -----------------------------------------------------------------------------
# Vehicle (ANPR) Schemas
# -----------------------------------------------------------------------------
class VehicleRegisterRequest(BaseModel):
    license_plate: str = Field(..., min_length=4, max_length=20, examples=["DL01AB1234"])
    vehicle_type: str = Field(default="car", examples=["jeep"])
    owner_name: Optional[str] = Field(None, examples=["Tactical Convoy Unit"])
    department: str = Field(default="Border Patrol", examples=["Border Patrol"])
    notes: Optional[str] = None

class VehicleResponse(BaseModel):
    id: str
    license_plate: str
    vehicle_type: str
    owner_name: Optional[str] = None
    department: str
    is_whitelisted: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
