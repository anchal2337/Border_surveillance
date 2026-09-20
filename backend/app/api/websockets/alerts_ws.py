import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.alert_dispatcher import alert_dispatcher

logger = logging.getLogger("websockets")
router = APIRouter()


@router.websocket("/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """
    Real-Time WebSocket Gateway for Perimeter Security Alerts.
    Connect here to receive instant push notifications for:
      - Perimeter intrusions
      - Tripwire breaches
      - Unidentified personnel / loitering
      - Speed / restricted zone violations
    """
    await alert_dispatcher.register_alert_client(websocket)
    try:
        while True:
            # Keep connection open and accept client heartbeats / control commands
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "PING":
                    await websocket.send_json({"event": "PONG", "status": "LIVE"})
            except Exception:
                pass
    except WebSocketDisconnect:
        alert_dispatcher.unregister_alert_client(websocket)
    except Exception as e:
        logger.warning("WebSocket alert error: %s", e)
        alert_dispatcher.unregister_alert_client(websocket)


@router.websocket("/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Real-Time WebSocket Gateway for Live Camera Telemetry & Sentry HUD.
    Pushes 1Hz updates of:
      - Actual Ingestion FPS
      - Active Track Counts
      - Maximum Threat Level
      - Frame counters & Carrier Status
    """
    await alert_dispatcher.register_telemetry_client(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "PING":
                    await websocket.send_json({"event": "PONG", "status": "LIVE"})
            except Exception:
                pass
    except WebSocketDisconnect:
        alert_dispatcher.unregister_telemetry_client(websocket)
    except Exception as e:
        logger.warning("WebSocket telemetry error: %s", e)
        alert_dispatcher.unregister_telemetry_client(websocket)
