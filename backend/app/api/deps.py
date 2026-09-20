from typing import Generator, List, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.constants import UserRole
from backend.app.core.security import decode_access_token
from backend.app.db.session import SessionLocal, get_db
from backend.app.models.entities import User

# OAuth2 scheme points to the login route for Swagger UI interactive login
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=True
)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts and validates the JWT Bearer token from the HTTP Authorization header,
    retrieves the user from SQLite, and verifies the account is active.
    """
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated sentry user not found.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sentry operator account is inactive or disabled.",
        )
    return user


class RoleChecker:
    """
    Dependency factory enforcing Role-Based Access Control (RBAC).
    Checks if the current authenticated user's role is within the allowed roles.
    """
    def __init__(self, allowed_roles: List[Union[UserRole, str]]):
        self.allowed_roles = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_role_str = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
        if user_role_str not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Operation requires one of the following roles: {self.allowed_roles}. Your role is '{user_role_str}'.",
            )
        return current_user


# Pre-configured RBAC dependencies for routes
require_super_admin = RoleChecker([UserRole.SUPER_ADMIN])
require_commander = RoleChecker([UserRole.COMMANDER, UserRole.SUPER_ADMIN])
require_operator = RoleChecker([UserRole.OPERATOR, UserRole.COMMANDER, UserRole.SUPER_ADMIN])
require_auditor = RoleChecker([UserRole.AUDITOR, UserRole.COMMANDER, UserRole.SUPER_ADMIN])
require_any_authenticated = get_current_user
