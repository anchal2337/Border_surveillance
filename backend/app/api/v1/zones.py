import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.entities import CameraZone, Camera, User
from backend.app.schemas.zone import (
    ZoneResponse,
    DynamicZoneCalibrationPayload,
)
from backend.app.services.camera_manager import camera_manager
from backend.app.api.deps import require_commander, get_current_user

router = APIRouter()

@router.get("/{camera_id}", response_model=List[ZoneResponse], summary="Get Active Zones & Tripwires")
def get_camera_zones(
    camera_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all geofence polygons and virtual tripwires registered for a camera."""
    return db.query(CameraZone).filter(CameraZone.camera_id == camera_id).all()

@router.post("/{camera_id}", summary="Dynamic Zone & Tripwire Calibration [COMMANDER or SUPER_ADMIN]")
def update_camera_zones_dynamically(
    camera_id: str,
    payload: DynamicZoneCalibrationPayload,
    current_user: User = Depends(require_commander),
    db: Session = Depends(get_db),
):
    """
    Instantly updates the geofence polygon and virtual tripwire vector coordinates.
    Saves new geometry to SQLite AND immediately updates the live AI computer vision
    pipeline in memory on the running camera worker with 0ms restart overhead.
    """
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera [{camera_id}] not found.")

    updated_zones = []

    # 1. Update Geofence Polygon if provided
    if payload.geofence is not None:
        geofence_zone = db.query(CameraZone).filter(
            CameraZone.camera_id == camera_id,
            CameraZone.zone_type == "GEOFENCE"
        ).first()

        coords_str = json.dumps(payload.geofence)
        if geofence_zone:
            geofence_zone.coordinates = coords_str
        else:
            geofence_zone = CameraZone(
                camera_id=camera_id,
                name="Calibrated Perimeter Geofence",
                zone_type="GEOFENCE",
                coordinates=coords_str,
                alert_on_entry=True,
                is_active=True,
            )
            db.add(geofence_zone)
        updated_zones.append("GEOFENCE")

    # 2. Update Virtual Tripwire if provided
    if payload.tripwire is not None:
        tripwire_zone = db.query(CameraZone).filter(
            CameraZone.camera_id == camera_id,
            CameraZone.zone_type == "TRIPWIRE"
        ).first()

        coords_str = json.dumps(payload.tripwire)
        if tripwire_zone:
            tripwire_zone.coordinates = coords_str
        else:
            tripwire_zone = CameraZone(
                camera_id=camera_id,
                name="Calibrated Tripwire Vector",
                zone_type="TRIPWIRE",
                coordinates=coords_str,
                alert_on_entry=True,
                is_active=True,
            )
            db.add(tripwire_zone)
        updated_zones.append("TRIPWIRE")

    db.commit()

    # 3. Live in-memory update to running AI worker!
    camera_manager.update_zones_live(
        camera_id=camera_id,
        geofence_pts=payload.geofence,
        tripwire_pts=payload.tripwire,
    )

    return {
        "status": "CALIBRATED",
        "camera_id": camera_id,
        "updated_zones": updated_zones,
        "message": f"Successfully updated {updated_zones} for camera [{camera_id}] in SQLite and live AI engine.",
    }
