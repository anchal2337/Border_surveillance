import os
import json
import logging
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.core.security import get_password_hash
from backend.app.db.session import engine, SessionLocal
from backend.app.db.base import Base
from backend.app.models.entities import (
    User,
    Camera,
    CameraZone,
    RegisteredPersonnel,
    RegisteredVehicle,
    Alert,
    EvidenceLocker,
    TrackSession,
    VehicleCrossing,
    AuditLog,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")

def init_db(clean_dynamic: bool = False) -> None:
    """
    Initializes pure SQLite database schema for 100% dynamic operations.
    Seeds only the essential Super Admin operator account.
    All cameras, alerts, evidence, and personnel are injected dynamically by the operator.
    """
    logger.info("Ensuring storage directories exist...")
    settings.ensure_directories()

    logger.info("Creating SQLite schema at %s ...", settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if clean_dynamic:
            logger.info("Purging all mock/seed data for a 100% dynamic environment...")
            db.query(Alert).delete()
            db.query(EvidenceLocker).delete()
            db.query(VehicleCrossing).delete()
            db.query(TrackSession).delete()
            db.query(CameraZone).delete()
            db.query(Camera).delete()
            db.commit()

        # 1. Seed Default Super Admin Operator (Required for login & RBAC)
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            logger.info("Seeding initial Super Admin operator (admin / admin123)...")
            admin_user = User(
                username="admin",
                email="commander@ibvap.mil",
                password_hash=get_password_hash("admin123"),
                full_name="Border Sentry Commander",
                role="SUPER_ADMIN",
                badge_number="BOP-CMD-01",
                department="Border Patrol Command HQ",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            logger.info("Super Admin operator created.")
        else:
            logger.info("Admin operator verified.")

        # 2. Provision default Local Webcam (CAM-USB) for immediate 1-click dynamic testing
        webcam = db.query(Camera).filter(Camera.id == "CAM-USB").first()
        if not webcam:
            logger.info("Provisioning Local Webcam channel (CAM-USB)...")
            webcam = Camera(
                id="CAM-USB",
                name="Local Webcam / USB Sensor",
                sector_zone="Command HQ",
                source_type="WEBCAM",
                stream_url="0",
                rtsp_transport="tcp",
                status="STANDBY",
                fps=30.0,
                resolution="1080x720",
                ai_pipeline="Edge Spatial CV + FRS",
                is_active=True,
            )
            db.add(webcam)
            db.commit()

            # Add default calibration zones for webcam
            geofence = CameraZone(
                camera_id="CAM-USB",
                name="Perimeter Security Zone",
                zone_type="GEOFENCE",
                coordinates=json.dumps([[150, 150], [930, 150], [930, 600], [150, 600]]),
                alert_on_entry=True,
                alert_on_exit=False,
                sensitivity=1.0,
                is_active=True,
            )
            tripwire = CameraZone(
                camera_id="CAM-USB",
                name="Tactical Breach Tripwire",
                zone_type="TRIPWIRE",
                coordinates=json.dumps([[100, 420], [980, 420]]),
                alert_on_entry=True,
                alert_on_exit=False,
                sensitivity=1.0,
                is_active=True,
            )
            db.add(geofence)
            db.add(tripwire)
            db.commit()

        logger.info("100% Dynamic Database schema initialized successfully.")

    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    init_db(clean_dynamic=True)
