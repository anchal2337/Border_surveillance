import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.entities import User, AuditLog
from backend.app.schemas.system import StorageHealthResponse, PruneRequest, PruneResponse
from backend.app.services.maintenance import retention_manager
from backend.app.api.deps import require_commander, require_super_admin

router = APIRouter()


@router.get("/storage", response_model=StorageHealthResponse, summary="Get Storage Health Metrics")
def get_system_storage(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_commander),
):
    """
    Returns comprehensive air-gapped system disk storage metrics,
    database size, evidence directory allocation, and health alerts.
    Permitted roles: COMMANDER, SUPER_ADMIN.
    """
    health = retention_manager.get_storage_health(db)
    return health


@router.post("/prune", response_model=PruneResponse, summary="Execute FIFO Storage Prune")
def prune_storage(
    payload: PruneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Triggers FIFO retention purge on transient CCTV evidence and crossing captures.
    Protects active cases and logs an immutable audit trail entry.
    Permitted role: SUPER_ADMIN.
    """
    files_pruned, bytes_freed = retention_manager.prune_old_records(
        db=db,
        max_age_days=payload.max_age_days or 30,
        max_storage_mb=payload.max_storage_mb,
    )

    # Non-repudiation audit trail
    audit = AuditLog(
        user_id=current_user.id,
        action="SYSTEM_STORAGE_PRUNED",
        entity_type="system",
        entity_id="storage",
        metadata_json=json.dumps({
            "files_pruned": files_pruned,
            "bytes_freed": bytes_freed,
            "max_age_days": payload.max_age_days,
            "initiated_by": current_user.username,
        }),
    )
    db.add(audit)
    db.commit()

    return {
        "files_removed": files_pruned,
        "bytes_reclaimed": bytes_freed,
        "status": "SUCCESS",
        "message": f"Successfully reclaimed {round(bytes_freed / (1024 * 1024), 2)} MB ({files_pruned} files).",
    }
