from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.session import get_db
from backend.app.models.entities import VehicleCrossing, User
from backend.app.schemas.crossing import VehicleCrossingResponse, VehicleCrossingSummary
from backend.app.api.deps import require_operator

router = APIRouter()


@router.get("", response_model=List[VehicleCrossingResponse], summary="List ANPR Vehicle Checkpoint Crossings")
def get_vehicle_crossings(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    license_plate: Optional[str] = Query(None, description="Search by license plate"),
    is_whitelisted: Optional[bool] = Query(None, description="Filter whitelisted vs unauthorized"),
    crossing_type: Optional[str] = Query(None, description="Filter by crossing type (e.g. 'Tripwire Breach', 'Geofence Intrusion')"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """
    Retrieves filtered list of ANPR vehicle crossings and checkpoint captures.
    Permitted roles: OPERATOR, COMMANDER, AUDITOR, SUPER_ADMIN.
    """
    query = db.query(VehicleCrossing)

    if camera_id:
        query = query.filter(VehicleCrossing.camera_id == camera_id)
    if license_plate:
        query = query.filter(VehicleCrossing.license_plate.ilike(f"%{license_plate}%"))
    if is_whitelisted is not None:
        query = query.filter(VehicleCrossing.is_whitelisted == is_whitelisted)
    if crossing_type:
        query = query.filter(VehicleCrossing.crossing_type.ilike(f"%{crossing_type}%"))

    records = query.order_by(desc(VehicleCrossing.crossed_at)).offset(offset).limit(limit).all()
    return records


@router.get("/summary", response_model=VehicleCrossingSummary, summary="ANPR Checkpoint Summary Statistics")
def get_crossings_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """Returns aggregated ANPR checkpoint crossing metrics for tactical sentry display."""
    total = db.query(VehicleCrossing).count()
    whitelisted = db.query(VehicleCrossing).filter(VehicleCrossing.is_whitelisted == True).count()
    unregistered = db.query(VehicleCrossing).filter(VehicleCrossing.is_whitelisted == False).count()
    latest = db.query(VehicleCrossing).order_by(desc(VehicleCrossing.crossed_at)).first()

    return VehicleCrossingSummary(
        total_crossings=total,
        whitelisted_count=whitelisted,
        unregistered_count=unregistered,
        latest_crossing_time=latest.crossed_at.isoformat() if latest else None,
    )


@router.get("/{crossing_id}", response_model=VehicleCrossingResponse, summary="Get Specific Vehicle Crossing")
def get_crossing_by_id(
    crossing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """Retrieves specific vehicle crossing record by ID."""
    record = db.query(VehicleCrossing).filter(VehicleCrossing.id == crossing_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Vehicle crossing [{crossing_id}] not found.")
    return record
