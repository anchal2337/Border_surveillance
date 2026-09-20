import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.constants import CameraStatus, CameraSourceType
from backend.app.db.session import get_db
from backend.app.models.entities import Camera, User
from backend.app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate
from backend.app.services.camera_manager import camera_manager
from backend.app.api.deps import require_commander, require_super_admin, get_current_user

router = APIRouter()

@router.get("", response_model=List[CameraResponse], summary="List All CCTV Cameras")
def list_cameras(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all registered CCTV cameras with real-time operational status,
    resolution, and current FPS telemetry.
    """
    cams = db.query(Camera).offset(skip).limit(limit).all()
    # Augment with live worker status
    for c in cams:
        status_info = camera_manager.get_status(c.id)
        if status_info["is_running"]:
            c.status = CameraStatus.ONLINE.value
            c.fps = status_info["fps"]
    return cams

@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED, summary="Register New CCTV Stream")
def create_camera(
    cam_in: CameraCreate,
    current_user: User = Depends(require_commander),
    db: Session = Depends(get_db),
):
    """Registers a new RTSP camera, webcam, or video source endpoint."""
    existing = db.query(Camera).filter(Camera.id == cam_in.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Camera with ID '{cam_in.id}' already exists.",
        )

    camera = Camera(
        id=cam_in.id,
        name=cam_in.name,
        sector_zone=cam_in.sector_zone,
        source_type=cam_in.source_type.value,
        stream_url=cam_in.stream_url,
        rtsp_transport=cam_in.rtsp_transport,
        status=CameraStatus.STANDBY.value,
        fps=cam_in.fps,
        resolution=cam_in.resolution,
        ai_pipeline=cam_in.ai_pipeline,
        is_active=True,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera

@router.post("/{camera_id}/connect", summary="Start Live AI Ingestion Worker")
def connect_camera(
    camera_id: str,
    current_user: User = Depends(require_commander),
    db: Session = Depends(get_db),
):
    """
    Launches a dedicated background ingestion thread for this camera stream.
    Begins real-time AI frame processing and updates the live /video_feed stream.
    """
    success = camera_manager.start_camera(camera_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera [{camera_id}] could not be found or started.",
        )
    return {
        "status": "CONNECTED",
        "camera_id": camera_id,
        "message": f"Camera [{camera_id}] live AI ingestion started successfully.",
        "stream_url": f"/api/v1/streams/{camera_id}/feed",
    }

@router.post("/{camera_id}/disconnect", summary="Stop Live Ingestion Worker")
def disconnect_camera(
    camera_id: str,
    current_user: User = Depends(require_commander),
    db: Session = Depends(get_db),
):
    """Stops the background ingestion worker and frees GPU/CPU memory."""
    camera_manager.stop_camera(camera_id, db)
    return {
        "status": "DISCONNECTED",
        "camera_id": camera_id,
        "message": f"Camera [{camera_id}] stream stopped.",
    }

@router.post("/upload-video", response_model=CameraResponse, summary="Upload CCTV Video & Stream Immediately")
async def upload_video_file(
    file: UploadFile = File(...),
    camera_id: str = Form(..., example="CAM-UPLOAD"),
    camera_name: str = Form(..., example="Recorded Drone Surveillance Replay"),
    sector_zone: str = Form(default="Sector 4", example="Sector 4"),
    current_user: User = Depends(require_commander),
    db: Session = Depends(get_db),
):
    """
    Uploads a CCTV video file (.mp4, .avi) directly to data/uploads/,
    registers it in SQLite, and connects it to the AI analytics engine immediately.
    """
    if not file.filename.lower().endswith((".mp4", ".avi", ".mkv", ".mov")):
        raise HTTPException(status_code=400, detail="Only video files (.mp4, .avi, .mkv, .mov) are supported.")

    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    destination = settings.UPLOADS_DIR / file.filename

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    relative_stream_url = f"data/uploads/{file.filename}"

    # Upsert camera record
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        cam = Camera(
            id=camera_id,
            name=camera_name,
            sector_zone=sector_zone,
            source_type=CameraSourceType.FILE.value,
            stream_url=relative_stream_url,
            status=CameraStatus.ONLINE.value,
            fps=30.0,
            resolution="1080x720",
            ai_pipeline="ByteTrack + FRS + ANPR + DQN",
            is_active=True,
        )
        db.add(cam)
    else:
        cam.name = camera_name
        cam.source_type = CameraSourceType.FILE.value
        cam.stream_url = relative_stream_url
        cam.status = CameraStatus.ONLINE.value

    db.commit()
    db.refresh(cam)

    # Immediately launch live processing
    camera_manager.start_camera(camera_id, db)

    return cam
