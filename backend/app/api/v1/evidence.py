import os
import json
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.config import settings
from backend.app.core.constants import EvidenceStatus, SeverityLevel
from backend.app.core.hashing import verify_evidence_integrity
from backend.app.db.session import get_db
from backend.app.models.entities import EvidenceLocker, User, AuditLog
from backend.app.schemas.evidence import (
    EvidenceResponse,
    EvidenceStatusUpdate,
    EvidenceVerifyResult,
)
from backend.app.api.deps import require_operator, require_commander, require_auditor

router = APIRouter()


@router.get("", response_model=List[EvidenceResponse], summary="List Forensic Evidence Cases")
def get_evidence_list(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity level"),
    evidence_status: Optional[EvidenceStatus] = Query(None, alias="status", description="Filter by investigation status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """
    Returns chain-of-custody evidence records collected during security incidents.
    Permitted roles: OPERATOR, COMMANDER, AUDITOR, SUPER_ADMIN.
    """
    query = db.query(EvidenceLocker)

    if camera_id:
        query = query.filter(EvidenceLocker.camera_id == camera_id)
    if severity:
        query = query.filter(EvidenceLocker.severity == severity.value)
    if evidence_status:
        query = query.filter(EvidenceLocker.status == evidence_status.value)

    records = query.order_by(desc(EvidenceLocker.created_at)).offset(offset).limit(limit).all()
    return records


@router.get("/{evidence_id}", response_model=EvidenceResponse, summary="Get Evidence Case Details")
def get_evidence_by_id(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """Retrieves specific forensic evidence case."""
    ev = db.query(EvidenceLocker).filter(EvidenceLocker.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence [{evidence_id}] not found.")
    return ev


@router.post("/{evidence_id}/verify", response_model=EvidenceVerifyResult, summary="Verify Evidence SHA-256 Hash")
def verify_evidence_hash(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """
    Cryptographically verifies the SHA-256 fingerprint of evidence on disk
    against the stored database signature to guarantee non-repudiation and prevent tampering.
    """
    ev = db.query(EvidenceLocker).filter(EvidenceLocker.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence [{evidence_id}] not found.")

    # Find the evidence file on disk
    file_path = None
    target_candidate = ev.crop_image or ev.scene_image
    if target_candidate:
        candidates = [
            Path(target_candidate),
            settings.DATA_DIR / target_candidate,
            settings.EVIDENCE_DIR / Path(target_candidate).name,
            settings.WORKSPACE_ROOT / target_candidate,
            settings.AI_CORE_DIR / target_candidate,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                file_path = str(c.resolve())
                break

    if not file_path:
        return EvidenceVerifyResult(
            is_valid=False,
            computed_hash="FILE_NOT_FOUND",
            expected_hash=ev.sha256_hash,
            file_path=target_candidate or "UNKNOWN",
            message="Evidence media file not found on server disk.",
        )

    is_valid, computed, expected = verify_evidence_integrity(file_path, ev.sha256_hash)
    msg = "Cryptographic integrity verified. Media matches original captured hash." if is_valid else "INTEGRITY VIOLATION: Media file hash does not match original capture hash!"

    return EvidenceVerifyResult(
        is_valid=is_valid,
        computed_hash=computed,
        expected_hash=expected,
        file_path=file_path,
        message=msg,
    )


@router.patch("/{evidence_id}/status", response_model=EvidenceResponse, summary="Update Investigation Status")
def update_evidence_status(
    evidence_id: str,
    payload: EvidenceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_commander),
):
    """
    Commanders update evidence investigation status (NEW -> INVESTIGATING -> CLOSED / DISMISSED).
    """
    ev = db.query(EvidenceLocker).filter(EvidenceLocker.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence [{evidence_id}] not found.")

    old_status = ev.status
    ev.status = payload.status.value
    if payload.resolution_notes:
        ev.resolution_notes = payload.resolution_notes

    # Add audit log entry
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="EVIDENCE_STATUS_UPDATED",
        entity_type="evidence",
        entity_id=ev.id,
        metadata_json=json.dumps({
            "old_status": old_status,
            "new_status": payload.status.value,
            "notes": payload.resolution_notes or "",
            "username": current_user.username,
        }),
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(ev)
    return ev
