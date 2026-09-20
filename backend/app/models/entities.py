import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin

def generate_uuid() -> str:
    return str(uuid.uuid4())

# -----------------------------------------------------------------------------
# 1. Users (Local Sentry & Operator Authentication)
# -----------------------------------------------------------------------------
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="OPERATOR", nullable=False)
    badge_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department: Mapped[str] = mapped_column(String(100), default="Border Patrol Command", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    acknowledged_alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="acknowledged_by_user")
    assigned_evidence: Mapped[List["EvidenceLocker"]] = relationship("EvidenceLocker", back_populates="assigned_user")


# -----------------------------------------------------------------------------
# 2. Cameras (Local Sensor Endpoints & Video Sources)
# -----------------------------------------------------------------------------
class Camera(Base, TimestampMixin):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. 'CAM-01', 'BOP-04'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sector_zone: Mapped[str] = mapped_column(String(100), default="Sector 1", nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="RTSP", nullable=False)
    stream_url: Mapped[str] = mapped_column(String(500), nullable=False)
    rtsp_transport: Mapped[str] = mapped_column(String(10), default="tcp", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="STANDBY", nullable=False)
    fps: Mapped[float] = mapped_column(Float, default=25.0, nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), default="1080x720", nullable=False)
    ai_pipeline: Mapped[str] = mapped_column(String(100), default="ByteTrack + FRS + ANPR + DQN", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    zones: Mapped[List["CameraZone"]] = relationship("CameraZone", back_populates="camera", cascade="all, delete-orphan")
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="camera", cascade="all, delete-orphan")
    track_sessions: Mapped[List["TrackSession"]] = relationship("TrackSession", back_populates="camera", cascade="all, delete-orphan")


# -----------------------------------------------------------------------------
# 3. Camera Zones (Dynamic Geofences & Virtual Tripwires)
# -----------------------------------------------------------------------------
class CameraZone(Base, TimestampMixin):
    __tablename__ = "camera_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(20), default="GEOFENCE", nullable=False)
    coordinates: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded array: [[x1, y1], [x2, y2], ...]
    alert_on_entry: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_on_exit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sensitivity: Mapped[float] = mapped_column(Float, default=1.00, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    camera: Mapped["Camera"] = relationship("Camera", back_populates="zones")


# -----------------------------------------------------------------------------
# 4. Registered Personnel (Biometric FaceNet Whitelist)
# -----------------------------------------------------------------------------
class RegisteredPersonnel(Base, TimestampMixin):
    __tablename__ = "registered_personnel"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), default="Border Guard", nullable=False)
    badge_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department: Mapped[str] = mapped_column(String(100), default="Perimeter Security", nullable=False)
    face_embedding: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded list of 512 floats
    photo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    registered_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


# -----------------------------------------------------------------------------
# 5. Registered Vehicles (ANPR Whitelist Plates)
# -----------------------------------------------------------------------------
class RegisteredVehicle(Base, TimestampMixin):
    __tablename__ = "registered_vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(30), default="car", nullable=False)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[str] = mapped_column(String(100), default="Official Transport", nullable=False)
    is_whitelisted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registered_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


# -----------------------------------------------------------------------------
# 6. Track Sessions (Object Tracking Kinematics & Association Cache)
# -----------------------------------------------------------------------------
class TrackSession(Base):
    __tablename__ = "track_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    class_name: Mapped[str] = mapped_column(String(50), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    max_threat_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dominant_behavior: Mapped[str] = mapped_column(String(50), default="Normal", nullable=False)
    resolved_identity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_authorized: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    current_speed_px_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_dwell_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trajectory_points: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON-encoded array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    camera: Mapped["Camera"] = relationship("Camera", back_populates="track_sessions")


# -----------------------------------------------------------------------------
# 7. Alerts (Real-Time Perimeter Security Incidents)
# -----------------------------------------------------------------------------
class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. 'ALT-1741200000-001'
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_session_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("track_sessions.id", ondelete="SET NULL"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="WARNING", nullable=False, index=True)
    threat_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    behavior: Mapped[str] = mapped_column(String(50), default="Normal", nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    camera: Mapped["Camera"] = relationship("Camera", back_populates="alerts")
    acknowledged_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="acknowledged_alerts")


# -----------------------------------------------------------------------------
# 8. Evidence Locker (Forensic Cases with SHA-256 Checksums)
# -----------------------------------------------------------------------------
class EvidenceLocker(Base, TimestampMixin):
    __tablename__ = "evidence_locker"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. 'EV-20260912_153653-T30'
    camera_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    track_session_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("track_sessions.id", ondelete="SET NULL"), nullable=True)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    camera_name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), default="Sector 1 (Perimeter Zone)", nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    object_label: Mapped[str] = mapped_column(String(100), nullable=False)
    class_name: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="WARNING", nullable=False)
    threat_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    behavior: Mapped[str] = mapped_column(String(50), default="Normal", nullable=False)
    identity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    speed_px_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dwell_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    crop_image: Mapped[str] = mapped_column(String(255), nullable=False)
    scene_image: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="NEW", nullable=False, index=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    assigned_user: Mapped[Optional["User"]] = relationship("User", back_populates="assigned_evidence")


# -----------------------------------------------------------------------------
# 9. Vehicle Crossings (ANPR Checkpoint Logs)
# -----------------------------------------------------------------------------
class VehicleCrossing(Base):
    __tablename__ = "vehicle_crossings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    license_plate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    ocr_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(30), default="car", nullable=False)
    is_whitelisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    crossing_type: Mapped[str] = mapped_column(String(50), nullable=False)
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
    source_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    crossed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


# -----------------------------------------------------------------------------
# 10. Audit Logs (Military Non-Repudiation Audit Trail)
# -----------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

# Composite and performance indexes
Index("idx_alerts_severity_created", Alert.severity, Alert.created_at.desc())
Index("idx_evidence_status_created", EvidenceLocker.status, EvidenceLocker.created_at.desc())
