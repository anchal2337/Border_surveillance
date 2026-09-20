import asyncio
import json
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import WebSocket

logger = logging.getLogger("alert_dispatcher")


class AlertDispatcher:
    """
    Central Pub-Sub Hub and Real-Time WebSocket Broadcaster for:
      - Security intrusion alerts (Perimeter breaches, tripwires, unauthorized personnel)
      - Forensic evidence events
      - Real-time video ingestion telemetry
    
    Thread-safe: Can be invoked from background camera worker threads or async routes.
    """

    _instance = None
    _lock = threading.Lock()
    _alert_clients: List[WebSocket]
    _telemetry_clients: List[WebSocket]
    _clients_lock: threading.Lock
    _recent_alerts: deque
    _event_loop: Optional[asyncio.AbstractEventLoop]

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AlertDispatcher, cls).__new__(cls)
                cls._instance._alert_clients = []
                cls._instance._telemetry_clients = []
                cls._instance._clients_lock = threading.Lock()
                cls._instance._recent_alerts = deque(maxlen=100)
                cls._instance._event_loop = None
            return cls._instance

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Sets the active asyncio event loop for thread-safe cross-thread scheduling."""
        self._event_loop = loop

    # -------------------------------------------------------------------------
    # Alert WebSocket Client Management
    # -------------------------------------------------------------------------
    async def register_alert_client(self, websocket: WebSocket):
        """Registers a connected WebSocket for real-time alert broadcasts."""
        await websocket.accept()
        with self._clients_lock:
            self._alert_clients.append(websocket)
        logger.info("New alert WebSocket client connected. Total active: %d", len(self._alert_clients))

        # Send last 15 alerts immediately so client gets instant situational awareness
        recent_snapshot = list(self._recent_alerts)[-15:]
        if recent_snapshot:
            try:
                await websocket.send_json({
                    "event": "INITIAL_ALERT_BUFFER",
                    "count": len(recent_snapshot),
                    "alerts": recent_snapshot,
                })
            except Exception as e:
                logger.warning("Failed to send initial alert buffer: %s", e)

    def unregister_alert_client(self, websocket: WebSocket):
        """Removes a disconnected WebSocket client."""
        with self._clients_lock:
            if websocket in self._alert_clients:
                self._alert_clients.remove(websocket)
        logger.info("Alert WebSocket client disconnected. Remaining active: %d", len(self._alert_clients))

    # -------------------------------------------------------------------------
    # Telemetry WebSocket Client Management
    # -------------------------------------------------------------------------
    async def register_telemetry_client(self, websocket: WebSocket):
        """Registers a connected WebSocket for live video stream telemetry."""
        await websocket.accept()
        with self._clients_lock:
            self._telemetry_clients.append(websocket)
        logger.info("New telemetry WebSocket client connected. Total active: %d", len(self._telemetry_clients))

    def unregister_telemetry_client(self, websocket: WebSocket):
        """Removes a disconnected telemetry WebSocket client."""
        with self._clients_lock:
            if websocket in self._telemetry_clients:
                self._telemetry_clients.remove(websocket)

    # -------------------------------------------------------------------------
    # Dispatch Methods (Thread-Safe)
    # -------------------------------------------------------------------------
    def dispatch_alert(self, alert_payload: Dict[str, Any]):
        """
        Dispatches an alert to all active WebSocket clients.
        Callable from both sync background threads and async routines.
        """
        if "timestamp" not in alert_payload:
            alert_payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Cache in memory ring buffer
        self._recent_alerts.append(alert_payload)

        # Broadcast to clients
        if self._event_loop and not self._event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._async_broadcast_alert(alert_payload), self._event_loop)
        else:
            # Fallback if loop isn't captured yet
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._async_broadcast_alert(alert_payload), loop)
            except Exception:
                pass

    async def _async_broadcast_alert(self, payload: Dict[str, Any]):
        """Asynchronously sends JSON payload to all registered alert WebSockets."""
        with self._clients_lock:
            active_clients = list(self._alert_clients)

        dead_clients = []
        for ws in active_clients:
            try:
                await ws.send_json({
                    "event": "NEW_ALERT",
                    "data": payload,
                })
            except Exception:
                dead_clients.append(ws)

        if dead_clients:
            with self._clients_lock:
                for dc in dead_clients:
                    if dc in self._alert_clients:
                        self._alert_clients.remove(dc)

    def dispatch_telemetry(self, telemetry_payload: Dict[str, Any]):
        """Dispatches dynamic stream telemetry frame to telemetry WebSocket clients."""
        if not self._telemetry_clients:
            return

        if self._event_loop and not self._event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._async_broadcast_telemetry(telemetry_payload), self._event_loop)

    async def _async_broadcast_telemetry(self, payload: Dict[str, Any]):
        """Asynchronously sends telemetry data to registered telemetry WebSockets."""
        with self._clients_lock:
            active_clients = list(self._telemetry_clients)

        dead_clients = []
        for ws in active_clients:
            try:
                await ws.send_json({
                    "event": "STREAM_TELEMETRY",
                    "data": payload,
                })
            except Exception:
                dead_clients.append(ws)

        if dead_clients:
            with self._clients_lock:
                for dc in dead_clients:
                    if dc in self._telemetry_clients:
                        self._telemetry_clients.remove(dc)

    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns the most recent in-memory alerts for fast retrieval."""
        recent = list(self._recent_alerts)
        return recent[-limit:]


# Global singleton instance
alert_dispatcher = AlertDispatcher()
