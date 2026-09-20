import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.entities import User

client = TestClient(app)

@pytest.fixture(scope="module")
def admin_token():
    """Authenticate default admin and return bearer token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert data["role"] == "SUPER_ADMIN"
    return data["access_token"]

@pytest.fixture(scope="module")
def operator_token(admin_token):
    """Create and authenticate a sentry operator."""
    username = "test_sentry_operator"
    # Ensure cleanup
    db = SessionLocal()
    db.query(User).filter(User.username == username).delete()
    db.commit()
    db.close()

    # Admin creates operator
    create_res = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": username,
            "email": "operator_test@ibvap.mil",
            "password": "OperatorPass@123",
            "full_name": "Sentry Operator Ramesh",
            "role": "OPERATOR",
            "badge_number": "SENTRY-01",
            "department": "Fence Patrol",
        },
    )
    assert create_res.status_code == 201, f"Failed to create operator: {create_res.text}"

    # Operator logs in
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "OperatorPass@123"},
    )
    assert login_res.status_code == 200
    return login_res.json()["access_token"]

@pytest.fixture(scope="module")
def commander_token(admin_token):
    """Create and authenticate a tactical commander."""
    username = "test_bop_commander"
    db = SessionLocal()
    db.query(User).filter(User.username == username).delete()
    db.commit()
    db.close()

    create_res = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": username,
            "email": "commander_test@ibvap.mil",
            "password": "CommanderPass@123",
            "full_name": "Major Arvind Sharma",
            "role": "COMMANDER",
            "badge_number": "BOP-CMD-88",
            "department": "Sector Headquarters",
        },
    )
    assert create_res.status_code == 201

    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "CommanderPass@123"},
    )
    assert login_res.status_code == 200
    return login_res.json()["access_token"]

def test_login_invalid_password():
    """Verify login fails with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "WRONG_PASSWORD"},
    )
    assert response.status_code == 401

def test_get_me(admin_token):
    """Verify GET /api/v1/auth/me returns current user."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "SUPER_ADMIN"

def test_operator_rbac_permissions(operator_token):
    """Verify OPERATOR role access matrix."""
    # 1. Access to Operator endpoint: ALLOWED
    op_res = client.get(
        "/api/v1/auth/rbac-test/operator",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert op_res.status_code == 200
    assert op_res.json()["tier"] == "OPERATOR_LEVEL"

    # 2. Access to Commander endpoint: FORBIDDEN
    cmd_res = client.get(
        "/api/v1/auth/rbac-test/commander",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert cmd_res.status_code == 403

    # 3. Access to Admin endpoint: FORBIDDEN
    admin_res = client.get(
        "/api/v1/auth/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert admin_res.status_code == 403

    # 4. Creating users: FORBIDDEN
    create_res = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"username": "illegal", "email": "i@i.com", "password": "123", "full_name": "x"},
    )
    assert create_res.status_code == 403

def test_commander_rbac_permissions(commander_token):
    """Verify COMMANDER role access matrix."""
    # 1. Access to Operator endpoint: ALLOWED (Commander inherits operator clearance)
    op_res = client.get(
        "/api/v1/auth/rbac-test/operator",
        headers={"Authorization": f"Bearer {commander_token}"},
    )
    assert op_res.status_code == 200

    # 2. Access to Commander endpoint: ALLOWED
    cmd_res = client.get(
        "/api/v1/auth/rbac-test/commander",
        headers={"Authorization": f"Bearer {commander_token}"},
    )
    assert cmd_res.status_code == 200

    # 3. Access to Auditor endpoint: ALLOWED
    audit_res = client.get(
        "/api/v1/auth/rbac-test/auditor",
        headers={"Authorization": f"Bearer {commander_token}"},
    )
    assert audit_res.status_code == 200

    # 4. Access to Super Admin only endpoint: FORBIDDEN
    admin_res = client.get(
        "/api/v1/auth/rbac-test/admin-only",
        headers={"Authorization": f"Bearer {commander_token}"},
    )
    assert admin_res.status_code == 403

def test_super_admin_unrestricted_access(admin_token):
    """Verify SUPER_ADMIN has access to all operational tiers."""
    for endpoint in ["operator", "commander", "auditor", "admin-only"]:
        res = client.get(
            f"/api/v1/auth/rbac-test/{endpoint}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200, f"Admin was denied on {endpoint}"
