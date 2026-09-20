import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.entities import User

client = TestClient(app)


@pytest.fixture(scope="module")
def admin_token():
    """Logs in default admin and returns access token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def commander_token(admin_token):
    """Creates a commander user and returns token."""
    username = "test_cmd_platform"
    db = SessionLocal()
    db.query(User).filter(User.username == username).delete()
    db.commit()
    db.close()

    client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": username,
            "email": "cmd_platform@ibvap.mil",
            "password": "CmdPass@123",
            "full_name": "Major Arvind Singh",
            "role": "COMMANDER",
            "badge_number": "CMD-99",
            "department": "Border Surveillance HQ",
        },
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "CmdPass@123"},
    )
    assert login_res.status_code == 200
    return login_res.json()["access_token"]


def test_dashboard_summary(admin_token):
    response = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert "cameras" in data
    assert "alerts" in data
    assert "forensics" in data
    assert "whitelist" in data
    assert data["cameras"]["total"] >= 1


def test_alerts_lifecycle(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # 1. List alerts
    response = client.get("/api/v1/alerts", headers=headers)
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)

    # 2. Get alerts summary
    summary_resp = client.get("/api/v1/alerts/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert "total_alerts" in summary
    assert "critical_count" in summary

    # 3. If an alert exists, test acknowledge
    if alerts:
        target_id = alerts[0]["id"]
        ack_resp = client.post(
            f"/api/v1/alerts/{target_id}/acknowledge",
            json={"resolution_notes": "Patrol sentry dispatched and verified false trigger."},
            headers=headers,
        )
        assert ack_resp.status_code == 200
        ack_data = ack_resp.json()
        assert ack_data["is_acknowledged"] is True
        assert ack_data["acknowledged_by"] is not None


def test_evidence_list_and_verification(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # 1. List evidence records
    response = client.get("/api/v1/evidence", headers=headers)
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)

    # 2. If evidence exists, test SHA-256 verification
    if records:
        target_id = records[0]["id"]
        verify_resp = client.post(f"/api/v1/evidence/{target_id}/verify", headers=headers)
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert "is_valid" in verify_data
        assert "expected_hash" in verify_data


def test_whitelist_personnel_and_vehicle_lifecycle(commander_token):
    headers = {"Authorization": f"Bearer {commander_token}"}

    # 1. List personnel
    p_resp = client.get("/api/v1/whitelist/personnel", headers=headers)
    assert p_resp.status_code == 200

    # 2. Enroll personnel
    new_guard = {
        "full_name": "Naik Subedar Ramesh",
        "designation": "Perimeter Guard",
        "badge_number": "BSF-4421",
        "department": "Quick Reaction Team",
        "face_embedding": [0.05] * 512,
    }
    enroll_resp = client.post("/api/v1/whitelist/personnel", json=new_guard, headers=headers)
    assert enroll_resp.status_code == 201
    person_data = enroll_resp.json()
    assert person_data["full_name"] == "Naik Subedar Ramesh"
    person_id = person_data["id"]

    # 3. Register vehicle
    new_vehicle = {
        "license_plate": "ARMY99X01",
        "vehicle_type": "jeep",
        "owner_name": "Sector Commander Escort",
        "department": "Border Security Force",
        "notes": "Armored Patrol Vehicle",
    }
    v_resp = client.post("/api/v1/whitelist/vehicles", json=new_vehicle, headers=headers)
    assert v_resp.status_code == 201
    veh_data = v_resp.json()
    assert veh_data["license_plate"] == "ARMY99X01"
    veh_id = veh_data["id"]

    # 4. Trigger bidirectional sync
    sync_resp = client.post("/api/v1/whitelist/sync", headers=headers)
    assert sync_resp.status_code == 200
    assert sync_resp.json()["status"] == "SUCCESS"

    # 5. Revoke personnel and vehicle
    del_p_resp = client.delete(f"/api/v1/whitelist/personnel/{person_id}", headers=headers)
    assert del_p_resp.status_code == 200

    del_v_resp = client.delete(f"/api/v1/whitelist/vehicles/{veh_id}", headers=headers)
    assert del_v_resp.status_code == 200
