import os
import json
import shutil
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.entities import User, AuditLog
from backend.app.schemas.system import StorageHealthResponse, PruneRequest, PruneResponse
from backend.app.services.maintenance import retention_manager
from backend.app.api.deps import require_commander, require_super_admin, get_current_user

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


@router.get("/disk-metrics", summary="Real-time Disk & Storage Metrics")
def get_disk_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Returns real-time system disk and storage metrics for the tactical dashboard.
    Uses stdlib only (shutil.disk_usage + os.path.getsize) — no psutil required.
    """
    try:
        # --- Disk usage for the workspace root drive ---
        workspace = Path(settings.WORKSPACE_ROOT if hasattr(settings, "WORKSPACE_ROOT") else ".")
        disk = shutil.disk_usage(str(workspace.resolve()))

        total_gb  = round(disk.total  / (1024 ** 3), 2)
        used_gb   = round(disk.used   / (1024 ** 3), 2)
        free_gb   = round(disk.free   / (1024 ** 3), 2)
        used_pct  = round((disk.used / disk.total) * 100, 1)

        # --- SQLite DB file size ---
        db_path = workspace / "data" / "ibvap.db"
        db_size_mb = round(db_path.stat().st_size / (1024 ** 2), 2) if db_path.exists() else 0.0

        # --- Evidence directory size ---
        evidence_dir = workspace / "data" / "evidence"
        evidence_mb = 0.0
        if evidence_dir.exists():
            evidence_mb = round(
                sum(f.stat().st_size for f in evidence_dir.rglob("*") if f.is_file()) / (1024 ** 2), 2
            )

        # --- Uploads directory size ---
        uploads_dir = workspace / "data" / "uploads"
        uploads_mb = 0.0
        if uploads_dir.exists():
            uploads_mb = round(
                sum(f.stat().st_size for f in uploads_dir.rglob("*") if f.is_file()) / (1024 ** 2), 2
            )

        return {
            "status": "OK" if used_pct < 90 else ("WARNING" if used_pct < 95 else "CRITICAL"),
            "disk": {
                "total_gb":   total_gb,
                "used_gb":    used_gb,
                "free_gb":    free_gb,
                "used_pct":   used_pct,
            },
            "database_mb":    db_size_mb,
            "evidence_mb":    evidence_mb,
            "uploads_mb":     uploads_mb,
            "total_data_mb":  round(db_size_mb + evidence_mb + uploads_mb, 2),
            "timestamp":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Disk metrics unavailable: {exc}")
