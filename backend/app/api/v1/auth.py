import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    get_db,
    get_current_user,
    require_super_admin,
    require_commander,
    require_operator,
    require_auditor,
)
from backend.app.core.constants import UserRole
from backend.app.core.security import verify_password, get_password_hash, create_access_token
from backend.app.models.entities import User, AuditLog
from backend.app.schemas.auth import (
    UserLogin,
    Token,
    UserCreate,
    UserResponse,
    RoleUpdate,
)

router = APIRouter()

# -----------------------------------------------------------------------------
# 1. Login & Token Generation (Supports Swagger OAuth2 form & JSON payloads)
# -----------------------------------------------------------------------------
@router.post("/login", response_model=Token, summary="Sentry Operator Login")
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticates sentry credentials, updates last_login_at, and issues a signed JWT token
    with cryptographically embedded Role-Based Access Control (RBAC) claims.
    Supports both JSON body and application/x-www-form-urlencoded (for Swagger UI).
    """
    username = ""
    password = ""

    # Check content-type to handle both JSON and Form submissions
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        username = body.get("username", "")
        password = body.get("password", "")
    else:
        form_data = await request.form()
        username = form_data.get("username", "")
        password = form_data.get("password", "")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or tactical access pass.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Contact Post Commander.",
        )

    # Record login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Generate token with user_id and embedded role
    access_token = create_access_token(subject=user.id, role=user.role)

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )


# -----------------------------------------------------------------------------
# 2. Get Current Authenticated Profile
# -----------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse, summary="Get Current Operator Profile")
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated operator's profile, role, and badge number."""
    return current_user


# -----------------------------------------------------------------------------
# 3. User Management (RBAC Guarded)
# -----------------------------------------------------------------------------
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Sentry User [SUPER_ADMIN only]"
)
def create_user(
    user_in: UserCreate,
    current_admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Creates a new user with a specific role (OPERATOR, COMMANDER, AUDITOR).
    Restricted strictly to SUPER_ADMIN.
    """
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_in.username}' already registered.",
        )
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_in.email}' already registered.",
        )

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role.value if isinstance(user_in.role, UserRole) else str(user_in.role),
        badge_number=user_in.badge_number,
        department=user_in.department,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record military audit log
    audit_entry = AuditLog(
        user_id=current_admin.id,
        action="USER_CREATED",
        entity_type="user",
        entity_id=new_user.id,
        metadata_json=json.dumps({"created_username": new_user.username, "role": new_user.role}),
    )
    db.add(audit_entry)
    db.commit()

    return new_user


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List All Sentry Users [COMMANDER or SUPER_ADMIN]"
)
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_commander),
    db: Session = Depends(get_db),
):
    """Lists all registered outpost operators. Requires COMMANDER or SUPER_ADMIN role."""
    return db.query(User).offset(skip).limit(limit).all()


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update Operator Role [SUPER_ADMIN only]"
)
def update_user_role(
    user_id: str,
    role_update: RoleUpdate,
    current_admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Promotes or changes an operator's role. Restricted strictly to SUPER_ADMIN."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    old_role = target_user.role
    target_user.role = role_update.role.value if isinstance(role_update.role, UserRole) else str(role_update.role)
    db.commit()
    db.refresh(target_user)

    # Audit log
    audit_entry = AuditLog(
        user_id=current_admin.id,
        action="USER_ROLE_UPDATED",
        entity_type="user",
        entity_id=target_user.id,
        metadata_json=json.dumps({"old_role": old_role, "new_role": target_user.role}),
    )
    db.add(audit_entry)
    db.commit()

    return target_user


# -----------------------------------------------------------------------------
# 4. RBAC Demonstration & Enforcement Verification Routes
# -----------------------------------------------------------------------------
@router.get("/rbac-test/operator", summary="Verify Operator Access")
def test_operator_access(current_user: User = Depends(require_operator)):
    """Accessible to OPERATOR, COMMANDER, and SUPER_ADMIN."""
    return {
        "status": "AUTHORIZED",
        "tier": "OPERATOR_LEVEL",
        "username": current_user.username,
        "role": current_user.role,
        "message": "Operator clearance verified. Granted access to live video feeds and alert monitoring.",
    }

@router.get("/rbac-test/commander", summary="Verify Commander Access")
def test_commander_access(current_user: User = Depends(require_commander)):
    """Accessible only to COMMANDER and SUPER_ADMIN."""
    return {
        "status": "AUTHORIZED",
        "tier": "COMMANDER_LEVEL",
        "username": current_user.username,
        "role": current_user.role,
        "message": "Tactical Commander clearance verified. Granted access to zone calibration and whitelist registry.",
    }

@router.get("/rbac-test/auditor", summary="Verify Auditor Access")
def test_auditor_access(current_user: User = Depends(require_auditor)):
    """Accessible only to AUDITOR, COMMANDER, and SUPER_ADMIN."""
    return {
        "status": "AUTHORIZED",
        "tier": "AUDITOR_LEVEL",
        "username": current_user.username,
        "role": current_user.role,
        "message": "Forensic Auditor clearance verified. Granted access to SHA-256 evidence verification.",
    }

@router.get("/rbac-test/admin-only", summary="Verify Super Admin Access")
def test_admin_access(current_user: User = Depends(require_super_admin)):
    """Accessible strictly to SUPER_ADMIN."""
    return {
        "status": "AUTHORIZED",
        "tier": "SUPER_ADMIN_LEVEL",
        "username": current_user.username,
        "role": current_user.role,
        "message": "Super Admin clearance verified. Granted full system and camera endpoint authority.",
    }
