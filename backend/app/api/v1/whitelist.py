import json
import uuid
from typing import List, Optional
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.entities import RegisteredPersonnel, RegisteredVehicle, User, AuditLog
from backend.app.schemas.whitelist import (
    FaceEnrollRequest,
    PersonnelResponse,
    VehicleRegisterRequest,
    VehicleResponse,
)
from backend.app.services.whitelist_sync import WhitelistSyncService
from backend.app.services.face_extractor import extract_face_embedding
from backend.app.api.deps import require_operator, require_commander, require_super_admin

try:
    from enhancement import apply_clahe
except Exception:
    def apply_clahe(frame, clip_limit=2.5, grid_size=(8, 8)):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
        cl = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)


router = APIRouter()
sync_service = WhitelistSyncService()


# -----------------------------------------------------------------------------
# Personnel (Face Recognition System - FRS) Whitelist
# -----------------------------------------------------------------------------
@router.get("/personnel", response_model=List[PersonnelResponse], summary="List Whitelisted Personnel")
def get_whitelisted_personnel(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """Returns all authorized border security personnel and whitelist registry."""
    records = db.query(RegisteredPersonnel).order_by(desc(RegisteredPersonnel.created_at)).offset(offset).limit(limit).all()
    return records


@router.post("/personnel", response_model=PersonnelResponse, status_code=status.HTTP_201_CREATED, summary="Enroll Authorized Personnel")
def enroll_personnel(
    payload: FaceEnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_commander),
):
    """
    Enrolls authorized personnel with facial biometric embedding.
    Immediately updates SQLite and synchronizes to registered_faces.json for AI engine.
    Permitted roles: COMMANDER, SUPER_ADMIN.
    """
    try:
        person = sync_service.register_personnel(
            db=db,
            full_name=payload.full_name,
            designation=payload.designation,
            face_embedding=payload.face_embedding,
            badge_number=payload.badge_number,
            department=payload.department,
            photo_path=payload.photo_path,
            registered_by_id=current_user.id,
        )

        audit = AuditLog(
            user_id=current_user.id,
            action="PERSONNEL_ENROLLED",
            entity_type="personnel",
            entity_id=person.id,
            metadata_json=json.dumps({"name": person.full_name, "designation": person.designation, "by": current_user.username}),
        )
        db.add(audit)
        db.commit()
        return person
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to enroll personnel: {str(e)}")


@router.post(
    "/personnel/upload-photo",
    response_model=PersonnelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll Personnel via Photo Upload (Auto-Embedding)",
)
async def upload_personnel_photo(
    photo: UploadFile = File(..., description="Border personnel portrait photo (JPEG/PNG)"),
    full_name: str = Form(..., description="Full Name of official"),
    designation: str = Form(..., description="Rank or Role"),
    badge_number: Optional[str] = Form(None, description="Military/Police badge identifier"),
    department: Optional[str] = Form("Perimeter Security", description="Assigned post/unit"),
    enhance: bool = Form(False, description="Apply CLAHE illumination normalization for low-light/harsh border sun"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_commander),
):
    """
    Enrolls authorized personnel directly from an uploaded facial portrait image.
    Automatically:
    1. Reads image bytes and decodes with OpenCV.
    2. Applies contrast-limited adaptive histogram equalization (CLAHE) if requested.
    3. Saves high-res photo in evidence storage under /data/evidence/faces/.
    4. Extracts 512-dimensional facial embedding vector using MTCNN + InceptionResnetV1.
    5. Persists personnel record into SQLite and syncs live to registered_faces.json.
    Permitted roles: COMMANDER, SUPER_ADMIN.
    """
    contents = await photo.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded photo is empty.")

    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Invalid or corrupt image format. Must be JPEG, PNG, or BMP.")

    if enhance:
        img_bgr = apply_clahe(img_bgr)

    faces_dir = settings.EVIDENCE_DIR / "faces"
    faces_dir.mkdir(parents=True, exist_ok=True)
    clean_filename = f"{uuid.uuid4().hex[:12]}_{photo.filename.replace(' ', '_')}"
    target_path = faces_dir / clean_filename

    cv2.imwrite(str(target_path), img_bgr)
    relative_photo_url = f"/data/evidence/faces/{clean_filename}"

    try:
        embedding = extract_face_embedding(img_bgr, allow_fallback=True)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Biometric embedding extraction failed: {str(e)}")

    try:
        person = sync_service.register_personnel(
            db=db,
            full_name=full_name,
            designation=designation,
            face_embedding=embedding,
            badge_number=badge_number,
            department=department,
            photo_path=relative_photo_url,
            registered_by_id=current_user.id,
        )

        audit = AuditLog(
            user_id=current_user.id,
            action="PERSONNEL_ENROLLED_PHOTO",
            entity_type="personnel",
            entity_id=person.id,
            metadata_json=json.dumps({
                "name": person.full_name,
                "designation": person.designation,
                "photo_path": relative_photo_url,
                "enhanced": enhance,
                "by": current_user.username,
            }),
        )
        db.add(audit)
        db.commit()
        return person
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to enroll personnel via photo: {str(e)}")


@router.delete("/personnel/{person_id}", summary="Revoke Authorized Personnel")
def delete_personnel(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_commander),
):
    """Revokes personnel authorization and re-syncs biometric whitelist."""
    person = db.query(RegisteredPersonnel).filter(RegisteredPersonnel.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail=f"Personnel [{person_id}] not found.")

    person_name = person.full_name
    db.delete(person)
    db.commit()

    # Re-sync JSON file
    sync_service.sync_from_db_to_json(db)

    audit = AuditLog(
        user_id=current_user.id,
        action="PERSONNEL_REVOKED",
        entity_type="personnel",
        entity_id=person_id,
        metadata_json=json.dumps({"name": person_name, "by": current_user.username}),
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Personnel [{person_name}] revoked successfully."}


# -----------------------------------------------------------------------------
# Vehicle (ANPR) Whitelist
# -----------------------------------------------------------------------------
@router.get("/vehicles", response_model=List[VehicleResponse], summary="List Whitelisted Vehicles")
def get_whitelisted_vehicles(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """Returns all authorized border patrol and official vehicles."""
    vehicles = db.query(RegisteredVehicle).order_by(desc(RegisteredVehicle.created_at)).offset(offset).limit(limit).all()
    return vehicles


@router.post("/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED, summary="Register Whitelisted Vehicle")
def register_vehicle(
    payload: VehicleRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_commander),
):
    """
    Registers an authorized vehicle plate.
    Immediately updates SQLite and synchronizes to registered_vehicles.json for AI engine.
    Permitted roles: COMMANDER, SUPER_ADMIN.
    """
    try:
        vehicle = sync_service.register_vehicle(
            db=db,
            license_plate=payload.license_plate,
            vehicle_type=payload.vehicle_type,
            owner_name=payload.owner_name,
            department=payload.department,
            notes=payload.notes,
            registered_by_id=current_user.id,
        )

        audit = AuditLog(
            user_id=current_user.id,
            action="VEHICLE_WHITELISTED",
            entity_type="vehicle",
            entity_id=vehicle.id,
            metadata_json=json.dumps({"plate": vehicle.license_plate, "owner": vehicle.owner_name or "", "by": current_user.username}),
        )
        db.add(audit)
        db.commit()
        return vehicle
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to register vehicle: {str(e)}")


@router.delete("/vehicles/{vehicle_id}", summary="Revoke Authorized Vehicle")
def delete_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_commander),
):
    """Revokes authorized vehicle plate and re-syncs ANPR whitelist."""
    vehicle = db.query(RegisteredVehicle).filter(RegisteredVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle [{vehicle_id}] not found.")

    plate = vehicle.license_plate
    db.delete(vehicle)
    db.commit()

    # Re-sync JSON file
    sync_service.sync_from_db_to_json(db)

    audit = AuditLog(
        user_id=current_user.id,
        action="VEHICLE_REVOKED",
        entity_type="vehicle",
        entity_id=vehicle_id,
        metadata_json=json.dumps({"plate": plate, "by": current_user.username}),
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Vehicle plate [{plate}] revoked successfully."}


# -----------------------------------------------------------------------------
# Bidirectional Sync Endpoint
# -----------------------------------------------------------------------------
@router.post("/sync", summary="Force Bidirectional Whitelist Sync")
def trigger_whitelist_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_commander),
):
    """
    Forces bidirectional synchronization between SQLite and AI Core JSON registries.
    Useful after manual editing of JSON files or system restore.
    """
    import_results = sync_service.sync_from_json_to_db(db)
    sync_service.sync_from_db_to_json(db)
    return {
        "status": "SUCCESS",
        "message": "Bidirectional whitelist synchronization completed.",
        "results": import_results,
    }
