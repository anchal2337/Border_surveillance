from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.core.constants import CameraStatus, SeverityLevel, EvidenceStatus
from backend.app.db.session import get_db
from backend.app.models.entities import (
    Camera,
    Alert,
    EvidenceLocker,
    RegisteredPersonnel,
    RegisteredVehicle,
    User,
)
from backend.app.services.camera_manager import camera_manager
from backend.app.api.deps import require_operator

router = APIRouter()


@router.get("/summary", summary="Central Command & Control Dashboard Metrics")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> Dict[str, Any]:
    """
    Returns consolidated tactical telemetry for the primary Command & Control display:
      - Camera fleet status (Online, Standby, Error)
      - Alert metrics (Critical, High Threat, Unacknowledged)
      - Active video streaming stats
      - Biometric and Vehicle whitelist counts
    """
    # 1. Camera Fleet Statistics
    total_cameras = db.query(Camera).count()
    online_cameras = db.query(Camera).filter(Camera.status == CameraStatus.ONLINE.value).count()
    standby_cameras = db.query(Camera).filter(Camera.status == CameraStatus.STANDBY.value).count()

    # Active stream workers from CameraManager singleton
    active_worker_ids = [cid for cid, w in camera_manager.workers.items() if w.is_alive()]
    active_stream_count = len(active_worker_ids)

    # 2. Alert Statistics
    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = now - timedelta(hours=24)

    total_alerts_24h = db.query(Alert).filter(Alert.created_at >= twenty_four_hours_ago).count()
    unack_alerts = db.query(Alert).filter(Alert.is_acknowledged == False).count()
    critical_alerts = db.query(Alert).filter(Alert.severity == SeverityLevel.CRITICAL.value).count()
    high_threat_alerts = db.query(Alert).filter(Alert.threat_score >= 80).count()

    # 3. Evidence Locker
    total_evidence = db.query(EvidenceLocker).count()
    open_investigations = db.query(EvidenceLocker).filter(
        EvidenceLocker.status.in_([EvidenceStatus.NEW.value, EvidenceStatus.INVESTIGATING.value])
    ).count()

    # 4. Whitelist Registry
    personnel_count = db.query(RegisteredPersonnel).filter(RegisteredPersonnel.is_authorized == True).count()
    vehicle_count = db.query(RegisteredVehicle).filter(RegisteredVehicle.is_whitelisted == True).count()

    return {
        "status": "OPERATIONAL",
        "system_time": now.isoformat(),
        "cameras": {
            "total": total_cameras,
            "online": online_cameras,
            "standby": standby_cameras,
            "active_stream_workers": active_stream_count,
            "active_camera_ids": active_worker_ids,
        },
        "alerts": {
            "last_24h_total": total_alerts_24h,
            "pending_acknowledgement": unack_alerts,
            "critical": critical_alerts,
            "high_threat": high_threat_alerts,
        },
        "forensics": {
            "total_evidence_cases": total_evidence,
            "active_investigations": open_investigations,
        },
        "whitelist": {
            "authorized_personnel": personnel_count,
            "whitelisted_vehicles": vehicle_count,
        },
        "edge_platform": {
            "deployment": "100% On-Premise Air-Gapped",
            "storage_engine": "SQLite WAL Mode",
            "version": settings.VERSION,
        }
    }
