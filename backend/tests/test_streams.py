import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.camera_manager import camera_manager

client = TestClient(app)

@pytest.fixture(scope="module")
def admin_token():
    """Authenticate default admin and return bearer token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]

def test_list_cameras(admin_token):
    """Verify listing all configured cameras."""
    res = client.get(
        "/api/v1/cameras",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    cams = res.json()
    assert len(cams) >= 4
    cam_ids = [c["id"] for c in cams]
    assert "CAM-01" in cam_ids
    assert "CAM-04" in cam_ids

def test_connect_camera(admin_token):
    """Verify connecting to a camera starts the background ingestion worker."""
    res = client.post(
        "/api/v1/cameras/CAM-01/connect",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CONNECTED"
    assert data["camera_id"] == "CAM-01"

def test_camera_telemetry():
    """Verify live camera telemetry endpoint returns real-time metrics."""
    res = client.get("/api/v1/streams/CAM-01/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert data["camera_id"] == "CAM-01"
    assert "fps" in data
    assert "active_tracks" in data
    assert "max_threat" in data
    assert "engine_mode" in data

def test_camera_snapshot():
    """Verify single-frame JPEG snapshot returns valid JPEG binary."""
    # Give worker a moment to publish first frame
    time.sleep(0.5)
    res = client.get("/api/v1/streams/CAM-01/snapshot")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    # JPEG magic bytes: 0xFF, 0xD8
    assert res.content[:2] == b"\xff\xd8"

def test_live_mjpeg_stream_first_frame():
    """Verify live MJPEG stream yields multipart boundary and JPEG bytes."""
    broadcaster = camera_manager.get_broadcaster("CAM-01")
    assert broadcaster is not None
    gen = broadcaster.generate_mjpeg_stream(timeout=1.0)
    frame_chunk = next(gen)
    assert b"--frame" in frame_chunk
    assert b"Content-Type: image/jpeg" in frame_chunk
    assert len(frame_chunk) > 100

def test_dynamic_zone_calibration(admin_token):
    """Verify dynamically updating geofences and tripwires."""
    calib_payload = {
        "camera_id": "CAM-01",
        "geofence": [[120, 200], [800, 200], [900, 600], [100, 600]],
        "tripwire": [[150, 450], [850, 450]],
    }
    res = client.post(
        "/api/v1/zones/CAM-01",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=calib_payload,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CALIBRATED"

    # Query back
    zones_res = client.get(
        "/api/v1/zones/CAM-01",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert zones_res.status_code == 200
    zones = zones_res.json()
    assert len(zones) >= 2

def test_disconnect_camera(admin_token):
    """Verify disconnecting camera gracefully terminates worker."""
    res = client.post(
        "/api/v1/cameras/CAM-01/disconnect",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "DISCONNECTED"

    # Verify status is now not running
    telemetry = client.get("/api/v1/streams/CAM-01/telemetry").json()
    assert telemetry["fps"] == 0.0
