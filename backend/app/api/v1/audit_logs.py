from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.session import get_db
from backend.app.models.entities import AuditLog, User
from backend.app.schemas.audit import AuditLogResponse
from backend.app.api.deps import require_auditor

router = APIRouter()


@router.get("", response_model=List[AuditLogResponse], summary="Query Immutable Audit Trail")
def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action name (e.g. PERSONNEL_ENROLLED, ALERT_ACKNOWLEDGED)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. alert, evidence, personnel, vehicle)"),
    user_id: Optional[str] = Query(None, description="Filter by actor user ID"),
    start_time: Optional[datetime] = Query(None, description="Filter logs on or after timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter logs on or before timestamp"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auditor),
):
    """
    Retrieves system-wide immutable non-repudiation audit trail logs.
    Authorized for AUDITOR, COMMANDER, and SUPER_ADMIN roles.
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)

    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    return logs


@router.get("/{log_id}", response_model=AuditLogResponse, summary="Get Audit Log Entry")
def get_audit_log_by_id(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auditor),
):
    """
    Retrieves a specific audit trail record by unique sequential ID.
    """
    log_entry = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log entry [{log_id}] not found.",
        )
    return log_entry
