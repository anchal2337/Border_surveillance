from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.entities import Camera
from backend.app.schemas.telemetry import TelemetrySnapshot
from backend.app.services.camera_manager import camera_manager

router = APIRouter()

@router.get("/{camera_id}/feed", summary="Live Processed Multipart MJPEG Video Stream")
def get_live_video_feed(
    camera_id: str,
    db: Session = Depends(get_db),
):
    """
    High-performance, zero-latency multipart MJPEG live video stream.
    Returns: multipart/x-mixed-replace; boundary=frame
    
    Can be opened directly in any web browser or embedded in an HTML:
    `<img src="http://127.0.0.1:8000/api/v1/streams/CAM-01/feed" width="100%" />`
    
    If the camera worker is not currently running, it automatically launches it.
    """
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera [{camera_id}] not found.")

    # Automatically launch background ingestion worker if not active
    broadcaster = camera_manager.get_broadcaster(camera_id)
    if not broadcaster or not camera_manager.get_status(camera_id)["is_running"]:
        camera_manager.start_camera(camera_id, db)
        broadcaster = camera_manager.get_broadcaster(camera_id)

    if not broadcaster:
        raise HTTPException(status_code=500, detail="Failed to initialize stream broadcaster.")

    return StreamingResponse(
        broadcaster.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        },
    )

@router.get("/{camera_id}/snapshot", summary="Instant High-Resolution JPEG Snapshot")
def get_camera_snapshot(
    camera_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns the single latest annotated JPEG frame from the live video stream.
    Used for freezing frames, forensic captures, and HTML5 Canvas calibration.
    """
    broadcaster = camera_manager.get_broadcaster(camera_id)
    if not broadcaster or not camera_manager.get_status(camera_id)["is_running"]:
        camera_manager.start_camera(camera_id, db)
        broadcaster = camera_manager.get_broadcaster(camera_id)

    if not broadcaster:
        raise HTTPException(status_code=404, detail="Camera stream not available.")

    jpeg_bytes = broadcaster.get_latest_snapshot()
    if not jpeg_bytes:
        # Wait briefly for first frame
        import time
        for _ in range(10):
            time.sleep(0.1)
            jpeg_bytes = broadcaster.get_latest_snapshot()
            if jpeg_bytes:
                break

    if not jpeg_bytes:
        raise HTTPException(status_code=503, detail="No frame captured yet. Camera starting up.")

    return Response(content=jpeg_bytes, media_type="image/jpeg")

@router.get("/{camera_id}/telemetry", response_model=TelemetrySnapshot, summary="Live Camera Telemetry")
def get_camera_telemetry(camera_id: str):
    """Returns live telemetry (actual FPS, active tracks count, threat score, model confidences) for dashboard meters."""
    status_info = camera_manager.get_status(camera_id)
    conf = status_info.get("model_confidences")
    kwargs = {
        "camera_id": camera_id,
        "fps": status_info["fps"],
        "active_tracks": status_info["active_tracks"],
        "max_threat": status_info["max_threat"],
        "engine_mode": "SYNTHETIC_SENTRY" if status_info["synthetic_mode"] else "LIVE_AI_ANALYTICS",
    }
    if conf:
        kwargs["model_confidences"] = conf
    return TelemetrySnapshot(**kwargs)
