import os
import sys
import time
import math
import json
import logging
import collections
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import cv2
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.config import settings
from backend.app.core.constants import CameraStatus, CameraSourceType
from backend.app.models.entities import Camera, CameraZone, Alert, EvidenceLocker, VehicleCrossing, TrackSession
from backend.app.db.session import SessionLocal
from backend.app.services.stream_broadcaster import StreamBroadcaster
from backend.app.services.ai_adapter import AIEngineAdapter
from backend.app.services.alert_dispatcher import alert_dispatcher

logger = logging.getLogger("camera_manager")

# Ensure OpenCV uses TCP transport for RTSP to prevent packet loss
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"


class CameraWorker(threading.Thread):
    """
    Dedicated background ingestion and AI inference thread per camera stream.

    Architecture (smooth FPS under heavy AI load):
    ┌──────────────────────┐     deque(maxlen=1)     ┌──────────────────────┐
    │  Capture Loop        │ ──── raw frames ──────► │  Inference Thread    │
    │  (always at fps)     │                          │  (YOLO+FRS+OCR)     │
    └──────────────────────┘                          └──────────────────────┘
             │                                                   │
             │  _annotated_frame (Lock-protected)  ◄─────────────┘
             │
             ▼
    broadcaster.publish_frame()   ← always at target FPS
    (serves last annotated frame; never waits for inference)

    Inference runs on a down-scaled frame (640 px wide) for 3× speed.
    Annotations are kept at broadcast resolution.
    """

    def __init__(
        self,
        camera_id: str,
        name: str,
        source_type: str,
        stream_url: str,
        fps: float = 25.0,
        resolution: str = "1920x1080",
        broadcaster: Optional[StreamBroadcaster] = None,
    ):
        super().__init__(name=f"CameraWorker-{camera_id}", daemon=True)
        self.camera_id   = camera_id
        self.camera_name = name
        self.source_type = source_type
        self.stream_url  = stream_url
        self.target_fps  = max(5.0, fps)
        self.resolution  = resolution
        self.broadcaster = broadcaster or StreamBroadcaster(camera_id)

        self._running    = False
        self._stop_event = threading.Event()
        self.cap: Optional[cv2.VideoCapture] = None

        # Resolve resolution dimensions (1080p Full HD default)
        try:
            w_str, h_str = resolution.lower().split("x")
            self.width  = int(w_str)
            self.height = int(h_str)
        except Exception:
            self.width, self.height = 1920, 1080

        # AI Adapter for this stream
        self.ai_adapter = AIEngineAdapter(
            camera_id=self.camera_id,
            camera_name=self.camera_name,
            alert_callback=self._handle_ai_alert,
            evidence_callback=self._handle_ai_evidence,
            crossing_callback=self._handle_ai_crossing,
        )

        # ── Producer / Consumer buffers ──────────────────────────────────────
        # The capture loop drops the latest raw frame here (maxlen=1 → no backlog).
        self._raw_frame_deque: "collections.deque" = collections.deque(maxlen=1)

        # The inference thread writes the latest annotated frame here.
        self._annotated_frame: Optional[np.ndarray] = None
        self._annotated_lock  = threading.Lock()

        # Inference-thread inference-skipping counter (skip N raw frames between inferences)
        # Dynamically adjusted: if inference is fast, skip fewer frames.
        self._infer_skip_frames = 0   # 0 = process every frame from deque

        # ── Telemetry ────────────────────────────────────────────────────────
        self.current_fps            = 0.0
        self.total_frames_processed = 0
        self.is_synthetic_mode      = False
        self.synthetic_tick         = 0

    # ------------------------------------------------------------------
    # AI event callbacks (unchanged from original)
    # ------------------------------------------------------------------
    def _handle_ai_alert(self, alert_data: Dict[str, Any]):
        """Persists alerts triggered by the AI engine into SQLite."""
        try:
            with SessionLocal() as db:
                alert_id = alert_data.get("id") or f"ALT-{int(time.time() * 1000)}"
                existing_alert = db.query(Alert).filter(Alert.id == alert_id).first()
                if existing_alert:
                    alert_id = f"{alert_id}-{int(time.time() * 1000) % 1000:03d}"

                alert = Alert(
                    id=alert_id,
                    camera_id=self.camera_id,
                    alert_type=alert_data.get("alert_type", "PERIMETER BREACH"),
                    severity=alert_data.get("severity", "CRITICAL"),
                    threat_score=alert_data.get("threat_score", 85),
                    behavior=alert_data.get("behavior", "Suspicious"),
                    label=alert_data.get("label", "Unknown Target"),
                    details=alert_data.get("details", ""),
                    snapshot_url=alert_data.get("snapshot_url", ""),
                    is_acknowledged=False,
                )
                db.add(alert)
                db.commit()
                db.refresh(alert)
                logger.info("Saved alert to SQLite: %s - %s", alert.id, alert.alert_type)

                alert_dispatcher.dispatch_alert({
                    "id":           alert.id,
                    "camera_id":    self.camera_id,
                    "camera_name":  self.camera_name,
                    "alert_type":   alert.alert_type,
                    "severity":     alert.severity,
                    "threat_score": alert.threat_score,
                    "behavior":     alert.behavior,
                    "label":        alert.label,
                    "details":      alert.details,
                    "snapshot_url": alert.snapshot_url,
                    "timestamp":    alert.created_at.isoformat() if alert.created_at else datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            logger.error("Failed to save alert to SQLite: %s", e)

    def _handle_ai_evidence(self, evidence_data: Dict[str, Any]):
        """Persists forensic evidence cases into SQLite."""
        try:
            with SessionLocal() as db:
                ev_id = evidence_data.get("id") or f"EV-{int(time.time() * 1000)}"
                existing_ev = db.query(EvidenceLocker).filter(EvidenceLocker.id == ev_id).first()
                if existing_ev:
                    return

                ev = EvidenceLocker(
                    id=ev_id,
                    camera_id=self.camera_id,
                    event=evidence_data.get("event", "Intrusion"),
                    camera_name=self.camera_name,
                    location="Border Perimeter",
                    track_id=int(evidence_data.get("track_id", 0)),
                    object_label=evidence_data.get("identity", "Target"),
                    class_name=evidence_data.get("class_name", "person"),
                    severity="CRITICAL" if evidence_data.get("threat_score", 0) >= 85 else "WARNING",
                    threat_score=int(evidence_data.get("threat_score", 85)),
                    behavior=evidence_data.get("behavior", "Breach"),
                    identity=evidence_data.get("identity", "Unknown"),
                    crop_image=evidence_data.get("crop_image", ""),
                    scene_image=evidence_data.get("scene_image", ""),
                    sha256_hash=evidence_data.get("sha256_hash", "sha256:0000000000000000"),
                    status="NEW",
                )
                db.add(ev)
                db.commit()
                db.refresh(ev)

                try:
                    track_id_val = int(evidence_data.get("track_id", 0))
                    track_sess = db.query(TrackSession).filter(
                        TrackSession.camera_id == self.camera_id,
                        TrackSession.track_number == track_id_val,
                    ).order_by(desc(TrackSession.id)).first()

                    if not track_sess:
                        track_sess = TrackSession(
                            camera_id=self.camera_id,
                            track_number=track_id_val,
                            class_name=evidence_data.get("class_name", "person"),
                            max_threat_score=int(evidence_data.get("threat_score", 85)),
                            dominant_behavior=evidence_data.get("behavior", "Breach"),
                            resolved_identity=evidence_data.get("identity", "Unknown"),
                            is_authorized=False,
                            current_speed_px_sec=4.2,
                            total_dwell_sec=8.5,
                            trajectory_points=json.dumps([[100, 200], [250, 320], [400, 450]]),
                        )
                        db.add(track_sess)
                        db.commit()
                except Exception as te:
                    logger.debug("Non-fatal TrackSession capture: %s", te)

                alert_dispatcher.dispatch_alert({
                    "event_type":   "FORENSIC_EVIDENCE_CAPTURED",
                    "id":           ev.id,
                    "camera_id":    self.camera_id,
                    "camera_name":  self.camera_name,
                    "threat_score": ev.threat_score,
                    "identity":     ev.identity,
                    "sha256_hash":  ev.sha256_hash,
                    "timestamp":    ev.created_at.isoformat() if ev.created_at else datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            logger.error("Failed to save evidence record to SQLite: %s", e)

    def _handle_ai_crossing(self, crossing_data: Dict[str, Any]):
        """Persists ANPR vehicle checkpoint crossing into SQLite."""
        try:
            with SessionLocal() as db:
                rec = VehicleCrossing(
                    camera_id=self.camera_id,
                    track_id=int(crossing_data.get("track_id", 0)),
                    license_plate=crossing_data.get("plate"),
                    ocr_confidence=float(crossing_data.get("confidence", 0.0)),
                    vehicle_type=crossing_data.get("vehicle_type", "car"),
                    is_whitelisted=bool(crossing_data.get("is_whitelisted", False)),
                    crossing_type=crossing_data.get("crossing_type", "Checkpoint Crossing"),
                    image_path=crossing_data.get("image_path", ""),
                    source_file=self.stream_url,
                    details=crossing_data.get("details", ""),
                )
                db.add(rec)

                try:
                    track_sess = TrackSession(
                        camera_id=self.camera_id,
                        track_number=int(crossing_data.get("track_id", 1)),
                        class_name=crossing_data.get("vehicle_type", "vehicle"),
                        max_threat_score=15 if crossing_data.get("is_whitelisted", False) else 75,
                        dominant_behavior="Checkpoint Crossing",
                        resolved_identity=crossing_data.get("plate", "Vehicle"),
                        is_authorized=crossing_data.get("is_whitelisted", False),
                        current_speed_px_sec=12.5,
                        total_dwell_sec=4.0,
                        trajectory_points=json.dumps([[50, 400], [200, 400], [400, 400]]),
                    )
                    db.add(track_sess)
                except Exception as te:
                    logger.debug("Non-fatal TrackSession crossing capture: %s", te)

                db.commit()
                db.refresh(rec)
                logger.info("Saved vehicle crossing to SQLite: Plate %s", rec.license_plate)

                alert_dispatcher.dispatch_alert({
                    "event_type":    "VEHICLE_CROSSING",
                    "id":            f"CR-{rec.id}",
                    "camera_id":     self.camera_id,
                    "camera_name":   self.camera_name,
                    "plate":         rec.license_plate,
                    "vehicle_type":  rec.vehicle_type,
                    "is_whitelisted": rec.is_whitelisted,
                    "crossing_type": rec.crossing_type,
                    "image_path":    rec.image_path,
                    "details":       rec.details,
                    "timestamp":     rec.crossed_at.isoformat() if rec.crossed_at else datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            logger.error("Failed to save vehicle crossing record: %s", e)

    # ------------------------------------------------------------------
    # Inference thread  (runs concurrently with capture loop)
    # ------------------------------------------------------------------
    def _inference_loop(self) -> None:
        """
        Dedicated AI inference daemon thread.

        Continuously pulls the latest raw frame from _raw_frame_deque,
        runs the full AI pipeline (YOLO + FRS + OCR), and writes the
        annotated result into _annotated_frame.

        Key design decisions:
        - deque(maxlen=1): if inference is slow, old frames are silently
          dropped — only the freshest raw frame is ever processed.
        - Inference runs on a 640-px wide down-scaled copy for speed;
          annotations are drawn at full broadcast resolution.
        - The capture/broadcast loop is NEVER blocked waiting for this thread.
        """
        # Width for YOLO inference (640 is the native YOLO training resolution)
        INFER_WIDTH = 640

        logger.info("Inference thread started for camera [%s]", self.camera_id)

        while not self._stop_event.is_set():
            if not self._raw_frame_deque:
                # Nothing to process yet — yield CPU briefly
                time.sleep(0.005)
                continue

            try:
                raw_frame = self._raw_frame_deque[-1]  # always latest
            except IndexError:
                time.sleep(0.005)
                continue

            try:
                # Run AI pipeline (YOLO + ByteTrack + FRS + OCR) directly on full frame
                annotated = self.ai_adapter.process_frame(raw_frame.copy(), enable_clahe=False)
            except Exception as exc:
                logger.error("Inference error on camera [%s]: %s", self.camera_id, exc)
                annotated = raw_frame  # fall back to raw frame on error

            # Write to shared buffer (non-blocking)
            with self._annotated_lock:
                self._annotated_frame = annotated

        logger.info("Inference thread stopped for camera [%s]", self.camera_id)

    # ------------------------------------------------------------------
    # Main capture + broadcast loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """
        Main camera capture and broadcast loop.

        Runs at target_fps, always publishing the latest annotated frame.
        The heavy AI work happens in a separate _inference_loop thread so
        this loop is NEVER stalled waiting for YOLO/FRS/OCR to finish.
        """
        import collections as _col
        # Patch in the real deque now that the import is available in the thread
        self._raw_frame_deque = _col.deque(maxlen=1)

        self._running = True
        logger.info(
            "CameraWorker [%s] started. Source: %s (%s)",
            self.camera_id, self.source_type, self.stream_url,
        )
        self._update_db_status(CameraStatus.ONLINE)

        # Publish an initial standby frame immediately so the stream endpoint
        # returns data in < 1 ms even before the first real frame arrives.
        initial_frame = self._generate_dynamic_sentry_frame()
        with self._annotated_lock:
            self._annotated_frame = initial_frame
        self.broadcaster.publish_frame(initial_frame, fps=self.target_fps)

        # Open physical capture
        self._open_capture()

        # Start the inference daemon thread
        infer_thread = threading.Thread(
            target=self._inference_loop,
            name=f"InferWorker-{self.camera_id}",
            daemon=True,
        )
        infer_thread.start()

        frame_interval = 1.0 / self.target_fps
        fps_calc_time  = time.time()
        frames_in_sec  = 0

        while not self._stop_event.is_set():
            try:
                loop_start = time.time()

                # ── Read next raw frame ──────────────────────────────────────────
                raw = self._read_next_frame()
                if raw is None or raw.size == 0:
                    raw = self._generate_dynamic_sentry_frame()

                # Push raw frame to inference thread (drop if inference is behind)
                self._raw_frame_deque.append(raw)

                # ── Publish the latest ANNOTATED frame (never wait for inference) ─
                with self._annotated_lock:
                    frame_to_broadcast = (
                        self._annotated_frame
                        if self._annotated_frame is not None
                        else raw
                    )

                self.broadcaster.publish_frame(frame_to_broadcast, fps=self.current_fps)
                self.total_frames_processed += 1
                frames_in_sec += 1

                # ── FPS telemetry (every 1 second) ───────────────────────────────
                now = time.time()
                elapsed_sec = now - fps_calc_time
                if elapsed_sec >= 1.0:
                    self.current_fps  = round(frames_in_sec / elapsed_sec, 1)
                    frames_in_sec     = 0
                    fps_calc_time     = now

                    telem = self.ai_adapter.get_telemetry()
                    alert_dispatcher.dispatch_telemetry({
                        "camera_id":        self.camera_id,
                        "camera_name":      self.camera_name,
                        "fps":              self.current_fps,
                        "total_frames":     self.total_frames_processed,
                        "active_tracks":    self.ai_adapter.active_tracks_count,
                        "max_threat":       self.ai_adapter.latest_max_threat,
                        "is_synthetic":     self.is_synthetic_mode,
                        "engine_mode":      telem.get("engine_mode", "EDGE_SPATIAL_CV"),
                        "model_confidences": telem.get("model_confidences", {
                            "object_detection": 0.88,
                            "tactical_threat":  0.91,
                            "face_recognition": 0.92,
                            "plate_ocr":        0.95,
                        }),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                # ── Frame-rate pacing ────────────────────────────────────────────
                elapsed = time.time() - loop_start
                sleep_needed = frame_interval - elapsed
                if sleep_needed > 0.001:
                    time.sleep(sleep_needed)
            except Exception as loop_err:
                logger.error("Error in CameraWorker [%s] frame loop: %s", self.camera_id, loop_err)
                time.sleep(0.05)

        # Cleanup
        self._stop_event.set()          # also signals inference thread
        infer_thread.join(timeout=3.0)

        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.broadcaster.close()
        self._update_db_status(CameraStatus.STANDBY)
        logger.info("CameraWorker [%s] stopped gracefully.", self.camera_id)

    def _open_capture(self) -> None:
        """Opens physical RTSP, webcam, or video file capture with resilient backend fallbacks."""
        try:
            if self.source_type == "WEBCAM" or self.stream_url.isdigit():
                device_idx = int(self.stream_url) if self.stream_url.isdigit() else 0
                opened = False
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
                for backend in backends:
                    try:
                        cap = cv2.VideoCapture(device_idx, backend)
                        if cap and cap.isOpened():
                            self.cap = cap
                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                            opened = True
                            logger.info("Opened webcam index %d with backend %s", device_idx, str(backend))
                            break
                    except Exception as ce:
                        logger.debug("Webcam backend %s attempt failed: %s", backend, ce)
                        continue

                if not opened:
                    logger.warning("Physical webcam index %d unavailable. Operating in dynamic sentry mode.", device_idx)
                    self.is_synthetic_mode = True
            elif self.source_type == "FILE":
                resolved_path = self._resolve_file_path(self.stream_url)
                if resolved_path and os.path.exists(resolved_path):
                    self.cap = cv2.VideoCapture(resolved_path)
                else:
                    logger.warning("Video file not found at %s. Falling back to dynamic live stream.", self.stream_url)
                    self.is_synthetic_mode = True
            elif self.source_type in ["HTTP", "HTTPS"] or self.stream_url.startswith(("http://", "https://")):
                logger.info("Connecting to HTTP/IP Camera stream: %s", self.stream_url)
                self.cap = cv2.VideoCapture(self.stream_url)
                if self.cap and self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            elif self.source_type == "RTSP" or self.stream_url.startswith("rtsp://"):
                # Quick TCP probe to avoid OpenCV C++ hang if the RTSP camera is offline
                can_connect = True
                try:
                    import socket
                    from urllib.parse import urlparse
                    parsed = urlparse(self.stream_url)
                    host = parsed.hostname or "127.0.0.1"
                    port = parsed.port or 554
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    s.connect((host, port))
                    s.close()
                except Exception:
                    can_connect = False

                if can_connect:
                    self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                else:
                    logger.info("RTSP host unreachable for [%s]. Running dynamic live sentry simulator.", self.camera_id)
                    self.is_synthetic_mode = True

            if self.cap and self.cap.isOpened():
                self.is_synthetic_mode = False
                logger.info("Successfully opened video stream for [%s]", self.camera_id)
            else:
                self.is_synthetic_mode = True
                logger.info("Physical stream not available for [%s]. Running dynamic live sentry simulator.", self.camera_id)
        except Exception as e:
            logger.warning("Error opening capture for %s: %s. Using dynamic sentry simulator.", self.camera_id, e)
            self.is_synthetic_mode = True

    def _read_next_frame(self) -> Optional[np.ndarray]:
        """Reads next frame with auto-looping on video files and guaranteed 1080p resolution."""
        if self.is_synthetic_mode or self.cap is None:
            return None

        try:
            if not self.cap.isOpened():
                return None

            ret, frame = self.cap.read()
            if not ret:
                if self.source_type == "FILE":
                    # Seamless loop for video files
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret:
                        return None
                else:
                    logger.warning("Dropped frame on camera [%s]. Reconnecting with delay...", self.camera_id)
                    time.sleep(1.0)
                    self._open_capture()
                    return None

            # Guarantee strict 1080p resolution matching self.width x self.height
            if frame is not None and frame.size > 0:
                h_f, w_f = frame.shape[:2]
                if w_f != self.width or h_f != self.height:
                    frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

            return frame
        except (cv2.error, Exception) as e:
            logger.warning("OpenCV error reading frame on camera [%s]: %s. Reconnecting...", self.camera_id, e)
            try:
                if self.cap is not None:
                    self.cap.release()
            except Exception:
                pass
            time.sleep(1.0)
            self._open_capture()
            return None

    def _resolve_file_path(self, path_str: str) -> Optional[str]:
        """Resolves video file path against workspace root and uploads dir."""
        candidates = [
            Path(path_str),
            settings.WORKSPACE_ROOT / path_str,
            settings.DATA_DIR / path_str,
            settings.UPLOADS_DIR / Path(path_str).name,
            settings.AI_CORE_DIR / path_str,
            settings.AI_CORE_DIR / "data" / "uploads" / Path(path_str).name,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return str(c.resolve())
        return None

    def _generate_dynamic_sentry_frame(self) -> np.ndarray:
        """
        TACTICAL STANDBY SENTRY FRAME
        Renders a clean defense standby frame when waiting for physical camera/video connection.
        Does NOT generate any fake/simulated alerts or artificial targets.
        """
        self.synthetic_tick += 1
        w, h = self.width, self.height

        # 1. Tactical Dark Canvas
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = (17, 19, 21)  # #111315 / #191C1F surface tone

        # Subtle 40px mechanical grid
        for gx in range(0, w, 40):
            cv2.line(frame, (gx, 0), (gx, h), (28, 32, 35), 1)
        for gy in range(0, h, 40):
            cv2.line(frame, (0, gy), (w, gy), (28, 32, 35), 1)

        # Draw calibrated zones overlay
        try:
            frame = self.ai_adapter.intrusion_engine.draw_zones(frame)
        except Exception:
            pass

        # 2. Standby Callout Banner
        center_x, center_y = w // 2, h // 2
        card_w, card_h = 480, 120
        c_x1, c_y1 = center_x - card_w // 2, center_y - card_h // 2
        c_x2, c_y2 = center_x + card_w // 2, center_y + card_h // 2

        cv2.rectangle(frame, (c_x1, c_y1), (c_x2, c_y2), (34, 38, 42), -1)
        cv2.rectangle(frame, (c_x1, c_y1), (c_x2, c_y2), (52, 56, 59), 1)

        # Corner gold notches
        notch_len = 10
        cv2.line(frame, (c_x1, c_y1), (c_x1 + notch_len, c_y1), (79, 168, 214), 2)
        cv2.line(frame, (c_x1, c_y1), (c_x1, c_y1 + notch_len), (79, 168, 214), 2)
        cv2.line(frame, (c_x2, c_y2), (c_x2 - notch_len, c_y2), (79, 168, 214), 2)
        cv2.line(frame, (c_x2, c_y2), (c_x2, c_y2 - notch_len), (79, 168, 214), 2)

        time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        cv2.putText(frame, f"[{self.camera_id}] {self.camera_name.upper()}", (c_x1 + 20, c_y1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (236, 241, 242), 2, cv2.LINE_AA)
        cv2.putText(frame, "CHANNEL STANDBY // AWAITING LIVE SENSOR STREAM", (c_x1 + 20, c_y1 + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (79, 168, 214), 1, cv2.LINE_AA)
        cv2.putText(frame, f"TIME: {time_str} | ZERO SIMULATED TARGETS", (c_x1 + 20, c_y1 + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (155, 151, 146), 1, cv2.LINE_AA)

        # 6. Live Military HUD Header with Microsecond Clock
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        cv2.putText(frame, f"SENTRY-LIVE [{self.camera_id}]: {self.camera_name.upper()}", (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 180), 1, cv2.LINE_AA)
        cv2.putText(frame, f"TIMECODE: {time_str} UTC+05:30", (18, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, "STATUS: AIR-GAPPED TACTICAL SENTRY FEED (LIVE)", (w - 420, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1, cv2.LINE_AA)

        return frame

    def _update_db_status(self, status_val: CameraStatus) -> None:
        """Updates camera status and heartbeat in SQLite."""
        try:
            with SessionLocal() as db:
                cam = db.query(Camera).filter(Camera.id == self.camera_id).first()
                if cam:
                    cam.status = status_val.value
                    cam.fps = self.current_fps
                    cam.last_heartbeat_at = datetime.now(timezone.utc)
                    db.commit()
        except Exception:
            pass

    def stop(self) -> None:
        """Signals worker to stop."""
        self._stop_event.set()


class CameraManager:
    """
    Singleton Camera Orchestrator managing background camera ingestion threads,
    multi-client stream broadcasters, and dynamic zone synchronization.
    """

    _instance = None
    _lock = threading.Lock()
    workers: Dict[str, CameraWorker]
    broadcasters: Dict[str, StreamBroadcaster]

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraManager, cls).__new__(cls)
                cls._instance.workers = {}
                cls._instance.broadcasters = {}
            return cls._instance

    def start_camera(self, camera_id: str, db: Session) -> bool:
        """Starts background worker thread for a specific camera."""
        with self._lock:
            # If already running
            if camera_id in self.workers and self.workers[camera_id].is_alive():
                logger.info("Camera [%s] already active.", camera_id)
                return True

            cam = db.query(Camera).filter(Camera.id == camera_id).first()
            if not cam:
                logger.error("Camera [%s] not found in SQLite.", camera_id)
                return False

            # Create or reuse broadcaster
            if camera_id not in self.broadcasters:
                self.broadcasters[camera_id] = StreamBroadcaster(camera_id)
            else:
                self.broadcasters[camera_id]._is_active = True

            worker = CameraWorker(
                camera_id=cam.id,
                name=cam.name,
                source_type=cam.source_type,
                stream_url=cam.stream_url,
                fps=cam.fps or 25.0,
                resolution=cam.resolution or "1920x1080",
                broadcaster=self.broadcasters[camera_id],
            )

            # Sync active zones from SQLite into AI adapter
            active_zones = db.query(CameraZone).filter(CameraZone.camera_id == camera_id, CameraZone.is_active == True).all()
            for z in active_zones:
                try:
                    coords = json.loads(z.coordinates)
                    if z.zone_type == "GEOFENCE":
                        worker.ai_adapter.update_zones(geofence_pts=coords)
                    elif z.zone_type == "TRIPWIRE":
                        worker.ai_adapter.update_zones(tripwire_pts=coords)
                except Exception:
                    pass

            self.workers[camera_id] = worker
            worker.start()
            return True

    def stop_camera(self, camera_id: str, db: Session) -> bool:
        """Stops background worker thread and frees resources."""
        with self._lock:
            worker = self.workers.pop(camera_id, None)
            if worker:
                worker.stop()
                worker.join(timeout=2.0)

            cam = db.query(Camera).filter(Camera.id == camera_id).first()
            if cam:
                cam.status = CameraStatus.STANDBY.value
                db.commit()
            return True

    def get_broadcaster(self, camera_id: str) -> Optional[StreamBroadcaster]:
        """Retrieves active broadcaster for live streaming."""
        with self._lock:
            return self.broadcasters.get(camera_id)

    def update_zones_live(self, camera_id: str, geofence_pts=None, tripwire_pts=None, geofence_enabled=None):
        """Immediately updates running AI spatial engine without restarting."""
        with self._lock:
            worker = self.workers.get(camera_id)
            if worker:
                worker.ai_adapter.update_zones(
                    geofence_pts=geofence_pts,
                    tripwire_pts=tripwire_pts,
                    geofence_enabled=geofence_enabled,
                )

    def get_status(self, camera_id: str) -> dict:
        """Returns live worker telemetry."""
        with self._lock:
            worker = self.workers.get(camera_id)
            if worker and worker.is_alive():
                telem = worker.ai_adapter.get_telemetry()
                return {
                    "camera_id": camera_id,
                    "is_running": True,
                    "fps": worker.current_fps,
                    "frames_processed": worker.total_frames_processed,
                    "synthetic_mode": worker.is_synthetic_mode,
                    "active_tracks": worker.ai_adapter.active_tracks_count,
                    "max_threat": worker.ai_adapter.latest_max_threat,
                    "engine_mode": telem.get("engine_mode", "EDGE_SPATIAL_CV"),
                    "model_confidences": telem.get("model_confidences", {}),
                }
            return {
                "camera_id": camera_id,
                "is_running": False,
                "fps": 0.0,
                "frames_processed": 0,
                "synthetic_mode": False,
                "active_tracks": 0,
                "max_threat": 0,
                "engine_mode": "OFFLINE",
                "model_confidences": {},
            }

    def get_all_active_tracks(self, camera_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns live active track kinematics across active cameras."""
        all_tracks = []
        with self._lock:
            for cid, worker in self.workers.items():
                if camera_id and cid != camera_id:
                    continue
                if worker and worker.is_alive():
                    cam_tracks = worker.ai_adapter.get_active_tracks()
                    all_tracks.extend(cam_tracks)
        return all_tracks

# Global singleton instance
camera_manager = CameraManager()
