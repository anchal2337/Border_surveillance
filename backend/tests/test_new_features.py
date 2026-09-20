import io
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.db.session import SessionLocal
from backend.app.models.entities import User, VehicleCrossing, AuditLog, TrackSession

client = TestClient(app)


def get_auth_token(role: str = "SUPER_ADMIN", username: str = "test_admin") -> str:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@ibvap.internal",
                password_hash="fakehashdummyforjwtvalidationpurpose",
                full_name=f"Test {role}",
                role=role,
                badge_number=f"TEST-{role[:3]}",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return create_access_token(subject=user.id, role=user.role.value if hasattr(user.role, "value") else str(user.role))


# -----------------------------------------------------------------------------
# 1. Test Phase 6: ANPR Checkpoint Crossings
# -----------------------------------------------------------------------------
def test_crossings_endpoints():
    token = get_auth_token("COMMANDER", "cmd_crossing")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed a crossing record
    with SessionLocal() as db:
        rec = VehicleCrossing(
            camera_id="CAM-01",
            track_id=101,
            license_plate="BORDER-TEST-99",
            ocr_confidence=0.97,
            vehicle_type="truck",
            is_whitelisted=True,
            crossing_type="Checkpoint Tripwire Crossing",
            image_path="/data/vehicle_crossings/test.jpg",
            details="Test crossing event",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        crossing_id = rec.id

    # List crossings
    resp = client.get("/api/v1/crossings", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(c["license_plate"] == "BORDER-TEST-99" for c in data)

    # Get single crossing
    resp_single = client.get(f"/api/v1/crossings/{crossing_id}", headers=headers)
    assert resp_single.status_code == 200
    assert resp_single.json()["license_plate"] == "BORDER-TEST-99"

    # Summary
    resp_sum = client.get("/api/v1/crossings/summary", headers=headers)
    assert resp_sum.status_code == 200
    summary = resp_sum.json()
    assert "total_crossings" in summary
    assert "whitelisted_count" in summary
    assert "unregistered_count" in summary


# -----------------------------------------------------------------------------
# 2. Test Phase 7: Photo-based Face Biometric Enrollment
# -----------------------------------------------------------------------------
def test_personnel_photo_upload():
    token = get_auth_token("COMMANDER", "cmd_biometric")
    headers = {"Authorization": f"Bearer {token}"}

    # Create dummy 200x200 RGB image
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(img, (100, 100), 50, (200, 200, 200), -1)
    _, encoded = cv2.imencode(".jpg", img)
    photo_file = io.BytesIO(encoded.tobytes())

    resp = client.post(
        "/api/v1/whitelist/personnel/upload-photo",
        headers=headers,
        files={"photo": ("soldier_portrait.jpg", photo_file, "image/jpeg")},
        data={
            "full_name": "Major Vikram Batra",
            "designation": "Commanding Officer",
            "badge_number": "CO-13JAK",
            "department": "Sector 4 Command",
            "enhance": "true",
        },
    )
    assert resp.status_code == 201
    result = resp.json()
    assert result["full_name"] == "Major Vikram Batra"
    assert result["designation"] == "Commanding Officer"
    assert result["photo_path"].startswith("/data/evidence/faces/")


# -----------------------------------------------------------------------------
# 3. Test Phase 8: Audit Logs & Track Sessions
# -----------------------------------------------------------------------------
def test_audit_logs_endpoints():
    token = get_auth_token("AUDITOR", "auditor_user")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
    assert len(logs) > 0


def test_track_sessions_endpoints():
    token = get_auth_token("OPERATOR", "op_tracker")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed a track session
    with SessionLocal() as db:
        sess = TrackSession(
            camera_id="CAM-01",
            track_number=42,
            class_name="person",
            max_threat_score=90,
            dominant_behavior="Tripwire Breach",
            resolved_identity="Target #42",
            is_authorized=False,
            current_speed_px_sec=3.8,
            total_dwell_sec=14.2,
            trajectory_points="[[50, 100], [120, 200]]",
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)
        session_id = sess.id

    # Active tracks
    resp_active = client.get("/api/v1/tracks/active", headers=headers)
    assert resp_active.status_code == 200
    assert isinstance(resp_active.json(), list)

    # Historical tracks for camera
    resp_hist = client.get("/api/v1/tracks/CAM-01/history", headers=headers)
    assert resp_hist.status_code == 200
    items = resp_hist.json()
    assert any(s["track_number"] == 42 for s in items)

    # Single session detail
    resp_single = client.get(f"/api/v1/tracks/sessions/{session_id}", headers=headers)
    assert resp_single.status_code == 200
    assert resp_single.json()["track_number"] == 42


# -----------------------------------------------------------------------------
# 4. Test Phase 9: Telemetry Confidence Matrix
# -----------------------------------------------------------------------------
def test_telemetry_model_confidences():
    token = get_auth_token("OPERATOR", "op_telemetry")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/streams/CAM-01/telemetry", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "model_confidences" in data
    matrix = data["model_confidences"]
    assert "object_detection" in matrix
    assert "tactical_threat" in matrix
    assert "face_recognition" in matrix
    assert "plate_ocr" in matrix


# -----------------------------------------------------------------------------
# 5. Test Phase 10: System Storage & FIFO Retention Maintenance
# -----------------------------------------------------------------------------
def test_system_storage_and_prune():
    token_cmd = get_auth_token("COMMANDER", "cmd_sys")
    token_super = get_auth_token("SUPER_ADMIN", "super_sys")

    # Get storage health
    resp_storage = client.get("/api/v1/system/storage", headers={"Authorization": f"Bearer {token_cmd}"})
    assert resp_storage.status_code == 200
    health = resp_storage.json()
    assert "total_disk_bytes" in health
    assert "free_disk_bytes" in health
    assert "is_healthy" in health

    # Operator cannot prune (Forbidden)
    token_op = get_auth_token("OPERATOR", "op_sys")
    resp_op_prune = client.post(
        "/api/v1/system/prune",
        headers={"Authorization": f"Bearer {token_op}"},
        json={"max_age_days": 10},
    )
    assert resp_op_prune.status_code == 403

    # Super Admin can prune
    resp_prune = client.post(
        "/api/v1/system/prune",
        headers={"Authorization": f"Bearer {token_super}"},
        json={"max_age_days": 30},
    )
    assert resp_prune.status_code == 200
    prune_res = resp_prune.json()
    assert prune_res["status"] == "SUCCESS"
    assert "bytes_reclaimed" in prune_res
