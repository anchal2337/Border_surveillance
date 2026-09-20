import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.app.db.session import get_db
from backend.app.models.entities import Alert, User, AuditLog
from backend.app.schemas.alert import AlertResponse, AlertAcknowledge
from backend.app.core.constants import SeverityLevel
from backend.app.api.deps import get_current_user, require_operator, require_commander

router = APIRouter()


@router.get("", response_model=List[AlertResponse], summary="List and Filter Perimeter Alerts")
def get_alerts(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity level"),
    is_acknowledged: Optional[bool] = Query(None, description="Filter acknowledged status"),
    min_threat: Optional[int] = Query(None, ge=0, le=100, description="Minimum threat score"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """
    Retrieves filtered list of security alerts sorted chronologically (latest first).
    Permitted roles: OPERATOR, COMMANDER, AUDITOR, SUPER_ADMIN.
    """
    query = db.query(Alert)

    if camera_id:
        query = query.filter(Alert.camera_id == camera_id)
    if severity:
        query = query.filter(Alert.severity == severity.value)
    if is_acknowledged is not None:
        query = query.filter(Alert.is_acknowledged == is_acknowledged)
    if min_threat is not None:
        query = query.filter(Alert.threat_score >= min_threat)

    alerts = query.order_by(desc(Alert.created_at)).offset(offset).limit(limit).all()
    return alerts


@router.get("/summary", summary="Aggregated Alert Threat Statistics")
def get_alerts_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """
    Returns high-level situational awareness metrics for the tactical dashboard.
    """
    total = db.query(Alert).count()
    unacknowledged = db.query(Alert).filter(Alert.is_acknowledged == False).count()
    critical = db.query(Alert).filter(Alert.severity == SeverityLevel.CRITICAL.value).count()
    warning = db.query(Alert).filter(Alert.severity == SeverityLevel.WARNING.value).count()
    high_threat = db.query(Alert).filter(Alert.threat_score >= 80).count()

    latest_alert = db.query(Alert).order_by(desc(Alert.created_at)).first()

    return {
        "total_alerts": total,
        "unacknowledged_count": unacknowledged,
        "critical_count": critical,
        "warning_count": warning,
        "high_threat_count": high_threat,
        "latest_alert_time": latest_alert.created_at.isoformat() if latest_alert else None,
    }


@router.get("/{alert_id}", response_model=AlertResponse, summary="Get Alert Details")
def get_alert_by_id(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """Retrieves specific alert by ID."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert [{alert_id}] not found.")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse, summary="Acknowledge and Resolve Alert")
def acknowledge_alert(
    alert_id: str,
    payload: AlertAcknowledge,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """
    Operator or Commander acknowledges an active alert.
    Logs action to cryptographic audit trail.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert [{alert_id}] not found.")

    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    if payload.resolution_notes:
        alert.resolution_notes = payload.resolution_notes

    # Add audit log entry
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="ALERT_ACKNOWLEDGED",
        entity_type="alert",
        entity_id=alert.id,
        metadata_json=json.dumps({"notes": payload.resolution_notes or "", "username": current_user.username}),
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(alert)
    return alert
