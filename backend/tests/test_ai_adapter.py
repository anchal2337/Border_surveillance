import os
import json
import pytest
import numpy as np
from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.services.ai_adapter import AIEngineAdapter
from backend.app.services.whitelist_sync import WhitelistSyncService
from backend.app.models.entities import RegisteredPersonnel, RegisteredVehicle

def test_ai_adapter_initialization():
    """Verify AIEngineAdapter initializes cleanly without touching OutLiners_SIH."""
    adapter = AIEngineAdapter(camera_id="CAM-01", camera_name="Test Camera")
    assert adapter.camera_id == "CAM-01"
    assert adapter.intrusion_engine is not None
    assert hasattr(adapter, "process_frame")
    assert hasattr(adapter, "update_zones")

def test_ai_adapter_process_frame():
    """Verify processing a synthetic 720p frame returns valid annotated image."""
    adapter = AIEngineAdapter(camera_id="CAM-01")
    dummy_frame = np.zeros((720, 1080, 3), dtype=np.uint8)

    annotated = adapter.process_frame(dummy_frame)
    assert annotated is not None
    assert annotated.shape == (720, 1080, 3)

def test_dynamic_zone_calibration():
    """Verify runtime calibration of geofence and tripwire without restarting."""
    adapter = AIEngineAdapter(camera_id="CAM-01")
    new_geofence = [[100, 100], [500, 100], [500, 500], [100, 500]]
    new_tripwire = [[50, 250], [550, 250]]

    adapter.update_zones(geofence_pts=new_geofence, tripwire_pts=new_tripwire)

    assert adapter.intrusion_engine.geofence_polygon is not None
    assert len(adapter.intrusion_engine.geofence_polygon) == 4
    assert adapter.intrusion_engine.tripwire == ((50, 250), (550, 250))

def test_alert_callback_interception():
    """Verify alert callback is triggered when alert is dispatched."""
    received_alerts = []

    def on_alert(alert_data):
        received_alerts.append(alert_data)

    adapter = AIEngineAdapter(camera_id="CAM-01", alert_callback=on_alert)

    # Directly test the local alert dispatcher
    dummy_frame = np.zeros((720, 1080, 3), dtype=np.uint8)
    adapter._dispatch_local_alert(
        alert_type="TRIPWIRE BREACH",
        identifier="Track #99",
        details="Perimeter line traversed",
        threat_score=100,
        frame=dummy_frame,
        crop=dummy_frame[10:50, 10:50],
        track_id=99,
    )

    assert len(received_alerts) == 1
    alert = received_alerts[0]
    assert alert["alert_type"] == "TRIPWIRE BREACH"
    assert alert["threat_score"] == 100
    assert alert["camera_id"] == "CAM-01"

def test_telemetry_snapshot():
    """Verify live telemetry snapshot dictionary contains required fields."""
    adapter = AIEngineAdapter(camera_id="CAM-01")
    telemetry = adapter.get_telemetry()
    assert "camera_id" in telemetry
    assert "fps" in telemetry
    assert "active_tracks" in telemetry
    assert "max_threat" in telemetry
    assert "engine_mode" in telemetry

def test_whitelist_sync_service():
    """Verify two-way synchronization between SQLite and AI engine JSONs."""
    sync_service = WhitelistSyncService()
    db = SessionLocal()
    try:
        # Test Vehicle registration sync
        test_plate = "AR01XY9999"
        veh = sync_service.register_vehicle(
            db=db,
            license_plate=test_plate,
            vehicle_type="truck",
            owner_name="Special Ops Convoy",
        )
        assert veh.license_plate == test_plate
        assert veh.is_whitelisted is True

        # Check vehicle JSON file
        with open(sync_service.vehicles_json_path, "r", encoding="utf-8") as f:
            v_data = json.load(f)
            assert test_plate in v_data.get("plates", [])

        # Test Personnel face registration sync
        dummy_embedding = [0.05] * 512
        person = sync_service.register_personnel(
            db=db,
            full_name="Havildar Vikram Singh",
            designation="Senior Sentry Guard",
            face_embedding=dummy_embedding,
            badge_number="BOP-G-88",
        )
        assert person.full_name == "Havildar Vikram Singh"

        # Check face JSON file
        with open(sync_service.faces_json_path, "r", encoding="utf-8") as f:
            f_data = json.load(f)
            assert "Havildar Vikram Singh" in f_data
            assert len(f_data["Havildar Vikram Singh"]["embedding"]) == 512

        # Cleanup test DB entries
        db.delete(veh)
        db.delete(person)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    pytest.main(["-v", __file__])
