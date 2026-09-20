import os
import pytest
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.core.security import verify_password
from backend.app.core.hashing import compute_file_sha256, verify_evidence_integrity
from backend.app.db.session import engine, SessionLocal
from backend.app.models.entities import (
    User,
    Camera,
    CameraZone,
    Alert,
    EvidenceLocker,
)

def test_database_file_exists():
    """Verify data/ibvap.db file exists on disk."""
    db_path = settings.DATA_DIR / "ibvap.db"
    assert db_path.exists(), f"Database file not found at {db_path}"

def test_sqlite_pragmas():
    """Verify SQLite WAL mode and Foreign Keys are enabled."""
    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode;")).scalar()
        foreign_keys = conn.execute(text("PRAGMA foreign_keys;")).scalar()
        assert journal_mode.lower() == "wal", f"Expected 'wal', got {journal_mode}"
        assert foreign_keys == 1, f"Expected foreign_keys=1, got {foreign_keys}"

def test_seeded_admin_user():
    """Verify default admin user was created and password verifies."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        assert user is not None, "Admin user not found in database"
        assert user.role == "SUPER_ADMIN"
        assert verify_password("admin123", user.password_hash) is True
    finally:
        db.close()

def test_seeded_cameras_and_zones():
    """Verify seeded preset cameras and initial zones exist."""
    db = SessionLocal()
    try:
        cameras = db.query(Camera).all()
        assert len(cameras) >= 4, f"Expected >= 4 cameras, found {len(cameras)}"
        cam_ids = {c.id for c in cameras}
        assert "CAM-01" in cam_ids
        assert "CAM-04" in cam_ids

        # Check CAM-04 zones
        cam_04 = db.query(Camera).filter(Camera.id == "CAM-04").first()
        assert len(cam_04.zones) >= 2, "Expected at least 2 zones on CAM-04 (Geofence + Tripwire)"
    finally:
        db.close()

def test_create_and_query_alert():
    """Verify creating, querying, and updating an alert record."""
    db = SessionLocal()
    try:
        alert_id = "ALT-TEST-999"
        # Cleanup if exists
        db.query(Alert).filter(Alert.id == alert_id).delete()
        db.commit()

        new_alert = Alert(
            id=alert_id,
            camera_id="CAM-01",
            alert_type="GEOFENCE INTRUSION",
            severity="CRITICAL",
            threat_score=95,
            behavior="Sprinting",
            label="Track #42 (Intruder)",
            details="High-speed perimeter breach in restricted zone",
            snapshot_url="/data/evidence/test_crop.jpg",
            is_acknowledged=False,
        )
        db.add(new_alert)
        db.commit()

        # Query back
        queried = db.query(Alert).filter(Alert.id == alert_id).first()
        assert queried is not None
        assert queried.threat_score == 95
        assert queried.is_acknowledged is False

        # Acknowledge
        queried.is_acknowledged = True
        queried.resolution_notes = "Investigated by Sentry Guard A."
        db.commit()

        updated = db.query(Alert).filter(Alert.id == alert_id).first()
        assert updated.is_acknowledged is True
        assert updated.resolution_notes == "Investigated by Sentry Guard A."

        # Cleanup
        db.delete(updated)
        db.commit()
    finally:
        db.close()

def test_evidence_hashing_and_verification(tmp_path):
    """Verify SHA-256 evidence integrity hashing and tamper checking."""
    # Create dummy evidence image
    dummy_image = tmp_path / "EV-TEST_crop.jpg"
    dummy_image.write_bytes(b"Simulated raw JPEG evidence image bytes 12345")

    short_hash = compute_file_sha256(str(dummy_image), short=True)
    assert short_hash.startswith("sha256:")
    assert len(short_hash) == 23  # 'sha256:' (7) + 16 chars = 23

    # Verification passes with untouched file
    is_valid, computed, expected = verify_evidence_integrity(str(dummy_image), short_hash)
    assert is_valid is True

    # Tampering: modify file bytes
    dummy_image.write_bytes(b"TAMPERED bytes")
    is_tampered_valid, comp_tampered, _ = verify_evidence_integrity(str(dummy_image), short_hash)
    assert is_tampered_valid is False
    assert comp_tampered != short_hash

if __name__ == "__main__":
    pytest.main(["-v", __file__])
