import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.alert_dispatcher import alert_dispatcher


def test_websocket_alerts_connection_and_ping():
    client = TestClient(app)
    with client.websocket_connect("/ws/alerts") as ws:
        # Send PING
        ws.send_json({"action": "PING"})
        response = ws.receive_json()
        assert response.get("event") == "PONG"
        assert response.get("status") == "LIVE"


def test_websocket_telemetry_connection_and_ping():
    client = TestClient(app)
    with client.websocket_connect("/ws/telemetry") as ws:
        # Send PING
        ws.send_json({"action": "PING"})
        response = ws.receive_json()
        assert response.get("event") == "PONG"
        assert response.get("status") == "LIVE"


def test_alert_dispatcher_in_memory_buffer():
    alert_dispatcher.dispatch_alert({
        "id": "ALT-TEST-999",
        "camera_id": "CAM-01",
        "alert_type": "PERIMETER BREACH",
        "severity": "CRITICAL",
        "threat_score": 95,
    })

    recent = alert_dispatcher.get_recent_alerts(limit=5)
    assert len(recent) >= 1
    assert any(a.get("id") == "ALT-TEST-999" for a in recent)
