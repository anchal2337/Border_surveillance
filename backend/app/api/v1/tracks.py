from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.session import get_db
from backend.app.models.entities import TrackSession, User
from backend.app.schemas.track import ActiveTrackInfo, TrackSessionResponse
from backend.app.services.camera_manager import camera_manager
from backend.app.api.deps import require_operator

router = APIRouter()


@router.get("/active", response_model=List[ActiveTrackInfo], summary="Get Live Active Tracks")
def get_active_tracks(
    camera_id: Optional[str] = Query(None, description="Optional camera ID filter"),
    current_user: User = Depends(require_operator),
):
    """
    Returns real-time kinematic telemetry and spatial positions of all targets
    currently tracked across live camera feeds.
    """
    tracks = camera_manager.get_all_active_tracks(camera_id=camera_id)
    return tracks


@router.get("/{camera_id}/history", response_model=List[TrackSessionResponse], summary="Get Historical Track Sessions")
def get_camera_track_history(
    camera_id: str,
    threat_min: Optional[int] = Query(None, ge=0, le=100, description="Minimum threat score threshold"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """
    Retrieves historical tracking sessions, trajectories, and threat metrics
    for a specific surveillance camera post.
    """
    query = db.query(TrackSession).filter(TrackSession.camera_id == camera_id)

    if threat_min is not None:
        query = query.filter(TrackSession.max_threat_score >= threat_min)

    sessions = query.order_by(desc(TrackSession.created_at)).offset(offset).limit(limit).all()
    return sessions


@router.get("/sessions/{session_id}", response_model=TrackSessionResponse, summary="Get Track Session By ID")
def get_track_session_by_id(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
):
    """
    Retrieves full forensic details and trajectory vector array for an individual track session.
    """
    session = db.query(TrackSession).filter(TrackSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track session [{session_id}] not found.",
        )
    return session
