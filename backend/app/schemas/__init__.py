"""IBVAP Pydantic Schemas Package"""
from .auth import UserLogin, Token, TokenPayload, UserCreate, UserResponse, RoleUpdate
from .camera import CameraCreate, CameraUpdate, CameraResponse
from .zone import ZoneCreate, ZoneUpdate, ZoneResponse, DynamicZoneCalibrationPayload
from .alert import AlertAcknowledge, AlertResponse
from .evidence import EvidenceStatusUpdate, EvidenceResponse, EvidenceVerifyResult
from .whitelist import FaceEnrollRequest, PersonnelResponse, VehicleRegisterRequest, VehicleResponse
from .telemetry import TelemetrySnapshot

__all__ = [
    "UserLogin",
    "Token",
    "TokenPayload",
    "UserCreate",
    "UserResponse",
    "RoleUpdate",
    "CameraCreate",
    "CameraUpdate",
    "CameraResponse",
    "ZoneCreate",
    "ZoneUpdate",
    "ZoneResponse",
    "DynamicZoneCalibrationPayload",
    "AlertAcknowledge",
    "AlertResponse",
    "EvidenceStatusUpdate",
    "EvidenceResponse",
    "EvidenceVerifyResult",
    "FaceEnrollRequest",
    "PersonnelResponse",
    "VehicleRegisterRequest",
    "VehicleResponse",
    "TelemetrySnapshot",
]
