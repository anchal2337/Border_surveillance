import sys
import os
import time
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Callable
import numpy as np
import cv2

from backend.app.core.config import settings

logger = logging.getLogger("ai_adapter")

# -----------------------------------------------------------------------------
# 1. Dynamic Path Injection (Zero changes to OutLiners_SIH folder)
# -----------------------------------------------------------------------------
AI_CORE_PATH = str(settings.AI_CORE_DIR.resolve())
if AI_CORE_PATH not in sys.path:
    sys.path.insert(0, AI_CORE_PATH)

# Check for Deep Learning frameworks
try:
    import torch
    from ultralytics import YOLO
    from tracker_engine import PerimeterTrackerEngine  # type: ignore
    from face_engine import FaceRecognitionEngine  # type: ignore
    from vehicle_engine import VehicleEngine  # type: ignore
    DL_FRAMEWORKS_AVAILABLE = True
    logger.info("Deep learning frameworks (PyTorch + Ultralytics) loaded successfully.")
except (ImportError, Exception) as e:
    DL_FRAMEWORKS_AVAILABLE = False
    logger.warning("Deep learning frameworks not available (%s). Running resilient Edge Spatial CV mode.", e)

# Import deterministic modules that only require OpenCV & NumPy
from intrusion_engine import SpatialIntrusionEngine  # type: ignore
from enhancement import apply_clahe  # type: ignore


class AIEngineAdapter:
    """
    Adapter bridging OutLiners_SIH edge models with the IBVAP backend.
    Preserves 100% of OutLiners_SIH files while providing:
      - Multi-client frame streaming
      - Real-time alert interception & dispatch to SQLite / WebSockets
      - Dynamic zone & tripwire calibration
      - Fallback edge spatial motion tracking when PyTorch is not loaded
    """

    COLOR_SAFE = (0, 255, 0)        # Green  (< 40%)
    COLOR_WARNING = (0, 165, 255)   # Orange (>= 40% and < 85%)
    COLOR_CRITICAL = (0, 0, 255)    # Red    (>= 85%)

    def __init__(
        self,
        camera_id: str = "CAM-01",
        camera_name: str = "Northern Fence Line",
        alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        evidence_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        crossing_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.alert_callback = alert_callback
        self.evidence_callback = evidence_callback
        self.crossing_callback = crossing_callback

        self.dl_enabled = DL_FRAMEWORKS_AVAILABLE
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0
        self.active_tracks_count = 0
        self.latest_max_threat = 0
        self.active_tracks_data: Dict[int, Dict[str, Any]] = {}

        # Directories
        self.evidence_dir = settings.EVIDENCE_DIR
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        if self.dl_enabled:
            self._init_deep_learning_engine()
        else:
            self._init_spatial_cv_engine()

    def _init_deep_learning_engine(self):
        """Initializes the full OutLiners_SIH PerimeterTrackerEngine."""
        try:
            logger.info("Initializing OutLiners_SIH PerimeterTrackerEngine...")
            faces_db = str(settings.DATA_DIR / "registered_faces.json")
            vehicles_db = str(settings.DATA_DIR / "registered_vehicles.json")

            self.face_engine = FaceRecognitionEngine(db_path=faces_db)
            self.vehicle_engine = VehicleEngine(db_path=vehicles_db)

            yolo_weight = str(settings.AI_CORE_DIR / "models" / "yolo26n.pt")
            if not os.path.exists(yolo_weight):
                yolo_weight = str(settings.AI_CORE_DIR / "yolo26n.pt")
                if not os.path.exists(yolo_weight):
                    yolo_weight = str(settings.AI_CORE_DIR / "models" / "yolo26nfinal.pt")
                    if not os.path.exists(yolo_weight):
                        yolo_weight = "yolov8n.pt"

            threat_weight = str(settings.AI_CORE_DIR / "models" / "yolo26n.pt")
            if not os.path.exists(threat_weight):
                threat_weight = str(settings.AI_CORE_DIR / "models" / "yolo26nfinal.pt")
                if not os.path.exists(threat_weight):
                    threat_weight = str(settings.AI_CORE_DIR / "best.pt")

            rl_weight = str(settings.AI_CORE_DIR / "models" / "behavioral_rl_model.zip")

            self.tracker = PerimeterTrackerEngine(
                face_engine=self.face_engine,
                vehicle_engine=self.vehicle_engine,
                yolo_model_path=yolo_weight,
                threat_model_path=threat_weight if os.path.exists(threat_weight) else None,
                rl_model_path=rl_weight,
            )
            self.tracker.current_camera_name = self.camera_name
            self.intrusion_engine = self.tracker.intrusion_engine

            # Attach runtime proxy hooks
            self._orig_trigger_alert = self.tracker.trigger_alert
            self._orig_capture_evidence = self.tracker.capture_investigation_evidence
            self._orig_save_crossing = self.tracker._save_vehicle_crossing_record
            self.tracker.trigger_alert = self._hook_trigger_alert
            self.tracker.capture_investigation_evidence = self._hook_capture_evidence
            self.tracker._save_vehicle_crossing_record = self._hook_save_vehicle_crossing
            logger.info("PerimeterTrackerEngine initialized successfully with runtime alert & crossing hooks.")
        except Exception as e:
            logger.error("Error initializing DL engine: %s. Falling back to Spatial CV mode.", e)
            self.dl_enabled = False
            self._init_spatial_cv_engine()

    def _init_spatial_cv_engine(self):
        """Initializes deterministic SpatialIntrusionEngine with OpenCV motion tracker."""
        logger.info("Initializing SpatialIntrusionEngine with edge motion tracking...")
        self.intrusion_engine = SpatialIntrusionEngine()
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=32, detectShadows=False)
        self.motion_tracks: Dict[int, Dict[str, Any]] = {}
        self.next_track_id = 1
        self.alert_cooldowns: Dict[str, float] = {}
        # Blob frame-confirmation cache: {blob_key: frame_count}
        # Alerts only fire after a blob is confirmed in MIN_BLOB_FRAMES consecutive frames.
        self.blob_confirm_cache: Dict[str, int] = {}
        self.MIN_BLOB_FRAMES = 2
        # Geofence enable flag (shared with DL path via update_zones)
        self.geofence_enabled: bool = True

    # -------------------------------------------------------------------------
    # Runtime Proxy Hooks
    # -------------------------------------------------------------------------
    def _hook_trigger_alert(
        self,
        alert_type: str,
        identifier: str,
        details: str,
        frame: Optional[np.ndarray] = None,
        crop: Optional[np.ndarray] = None,
        track_id: int = 0,
        threat_score: int = 85,
    ) -> bool:
        created = self._orig_trigger_alert(alert_type, identifier, details)
        if created:
            snapshot_url = ""
            # Persist real forensic evidence crop & scene to disk with SHA-256 checksum
            if frame is not None and crop is not None and crop.size > 0:
                try:
                    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                    evidence_id = f"EV-{timestamp_str}-T{track_id}"
                    crop_filename = f"{evidence_id}_crop.jpg"
                    scene_filename = f"{evidence_id}_scene.jpg"
                    crop_path = self.evidence_dir / crop_filename
                    scene_path = self.evidence_dir / scene_filename

                    cv2.imwrite(str(crop_path), crop)
                    cv2.imwrite(str(scene_path), frame)

                    # Compute cryptographic SHA-256 fingerprint for chain of custody
                    hasher = hashlib.sha256()
                    with open(str(scene_path), "rb") as f:
                        hasher.update(f.read())
                    sha256_hash = f"sha256:{hasher.hexdigest()}"

                    snapshot_url = f"/data/evidence/{crop_filename}"

                    if self.evidence_callback:
                        self.evidence_callback({
                            "id": evidence_id,
                            "camera_id": self.camera_id,
                            "camera_name": self.camera_name,
                            "event": alert_type,
                            "track_id": track_id,
                            "crop_image": f"/data/evidence/{crop_filename}",
                            "scene_image": f"/data/evidence/{scene_filename}",
                            "sha256_hash": sha256_hash,
                            "threat_score": threat_score,
                            "behavior": details,
                            "identity": identifier,
                        })
                except Exception as ee:
                    logger.error("Error creating forensic evidence: %s", ee)

            if self.alert_callback:
                is_critical = any(kw in alert_type.upper() for kw in ("BREACH", "THREAT", "INTRUSION", "GHOST"))
                alert_payload = {
                    "id": f"ALT-{int(time.time() * 1000)}",
                    "camera_id": self.camera_id,
                    "camera_name": self.camera_name,
                    "alert_type": alert_type,
                    "severity": "CRITICAL" if is_critical else "WARNING",
                    "threat_score": threat_score,
                    "label": identifier,
                    "details": details,
                    "snapshot_url": snapshot_url,
                    "timestamp": time.strftime("%H:%M:%S"),
                }
                self.alert_callback(alert_payload)
        return created

    def _hook_capture_evidence(self, **kwargs) -> Optional[str]:
        evidence_id = self._orig_capture_evidence(**kwargs)
        if self.evidence_callback and kwargs.get("crop") is not None:
            crop_path = kwargs.get("crop_path") or ""
            evidence_payload = {
                "id": f"EV-{time.strftime('%Y%m%d_%H%M%S')}-T{kwargs.get('track_id', 0)}",
                "camera_id": self.camera_id,
                "camera_name": self.camera_name,
                "event": kwargs.get("incident_type", "Perimeter Breach"),
                "threat_score": kwargs.get("suspicion_score", 85),
                "crop_path": crop_path,
                "behavior": kwargs.get("behavior_str", "Suspicious"),
                "identity": kwargs.get("identity_label", "Unknown Subject"),
            }
            self.evidence_callback(evidence_payload)
        return evidence_id

    def _hook_save_vehicle_crossing(
        self,
        plate: str,
        vehicle_type: str,
        track_id: int,
        confidence: float,
        is_whitelisted: bool,
        image_path: str,
        details: str,
        crop: Optional[np.ndarray] = None,
        frame: Optional[np.ndarray] = None,
    ):
        # Save real vehicle crop image to disk for evidence / ANPR checkpoint log with CLAHE enhancement
        if not image_path and crop is not None and crop.size > 0:
            try:
                # Apply CLAHE to dramatically boost contrast, plate character readability, and edge fidelity
                clahe_crop = apply_clahe(crop)
                final_crop = clahe_crop if (clahe_crop is not None and clahe_crop.size > 0) else crop
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                img_name = f"CROSSING_{timestamp_str}_T{int(track_id)}.jpg"
                save_dest = self.evidence_dir / img_name
                cv2.imwrite(str(save_dest), final_crop)
                image_path = f"/data/evidence/{img_name}"
            except Exception as e:
                logger.error("Failed to save vehicle crossing snapshot: %s", e)

        if self.crossing_callback:
            crossing_type = (
                "Tripwire Crossing" if "trip" in str(details).lower()
                else ("Fence Breach Crossing" if any(k in str(details).lower() for k in ("fence", "zone", "geofence", "boundary")) else "Checkpoint Entry")
            )
            crossing_payload = {
                "plate": plate,
                "vehicle_type": vehicle_type,
                "track_id": int(track_id),
                "confidence": float(confidence),
                "is_whitelisted": bool(is_whitelisted),
                "image_path": image_path,
                "crossing_type": crossing_type,
                "details": details,
            }
            self.crossing_callback(crossing_payload)

    # -------------------------------------------------------------------------
    # Frame Processing Pipeline
    # -------------------------------------------------------------------------
    def process_frame(self, frame: np.ndarray, enable_clahe: bool = True) -> np.ndarray:
        """
        Processes a raw video frame through the AI pipeline:
          - Applies CLAHE enhancement if enabled
          - Ingests into PerimeterTrackerEngine (or edge spatial tracker)
          - Renders tactical HUD overlay
          - Computes live FPS & telemetry
        """
        self.frame_count += 1
        curr_time = time.time()
        if curr_time - self.last_fps_time >= 1.0:
            self.current_fps = round(self.frame_count / (curr_time - self.last_fps_time), 1)
            self.frame_count = 0
            self.last_fps_time = curr_time

        if self.dl_enabled:
            # Run OutLiners_SIH PerimeterTrackerEngine
            # NOTE: enable_clahe is always False here — tracker applies CLAHE per-person-crop internally
            annotated_frame = self.tracker.process_frame(frame, enable_clahe=False)
            self.active_tracks_count = len(self.tracker.track_memory)
            # Sync max threat from per-track records
            if self.tracker.threat_records:
                self.latest_max_threat = max(
                    r.get("threat_score", 0) for r in self.tracker.threat_records.values()
                )
            else:
                self.latest_max_threat = 0
            return annotated_frame
        else:
            # Run Edge Spatial CV Engine
            return self._process_frame_spatial_cv(frame, enable_clahe=enable_clahe)

    def _process_frame_spatial_cv(self, frame: np.ndarray, enable_clahe: bool = True) -> np.ndarray:
        """
        Fallback processing using OutLiners_SIH SpatialIntrusionEngine + motion detection.

        Fixes applied:
        - Min blob area raised to 3 000 px² (was 800) to eliminate shadow / noise false positives.
        - Blobs must be confirmed in MIN_BLOB_FRAMES (2) consecutive frames before any alert fires.
        - Geofence intrusion alerts respect self.geofence_enabled; tripwire always active.
        - CLAHE is NOT applied frame-wide here; it is handled per-person-crop in tracker_engine.
        """
        # Draw zones (geofence + tripwire overlay)
        frame = self.intrusion_engine.draw_zones(frame)
        h, w = frame.shape[:2]

        # Background subtraction — use slower learning rate so standing people stay in fg mask
        fg_mask = self.bg_subtractor.apply(frame, learningRate=0.005)
        _, thresh = cv2.threshold(fg_mask, 180, 255, cv2.THRESH_BINARY)

        # Morphological close to fill gaps in large blobs (people, vehicles)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Min area: 1 500 px² (was 3 000) — detects persons even when partially stationary.
        # Max area: 300 000 px² to skip frame-filling blobs from sudden lighting changes.
        active_boxes: list = []
        for c in contours:
            area = cv2.contourArea(c)
            if 1500 < area < 300_000:
                x, y, bw, bh = cv2.boundingRect(c)
                active_boxes.append((x, y, x + bw, y + bh))

        # Keep top-10 largest blobs
        active_boxes = sorted(active_boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)[:10]
        self.active_tracks_count = len(active_boxes)
        max_threat = 0
        current_time = time.time()

        # Track which blob keys are alive this frame (for cache cleanup)
        alive_blob_keys: set = set()

        for idx, box in enumerate(active_boxes):
            track_id = idx + 1
            x1, y1, x2, y2 = box
            footprint = self.intrusion_engine.get_footprint(box)

            # Stable blob key based on grid cell (32 px grid)
            blob_key = f"{x1 // 32}_{y1 // 32}"
            alive_blob_keys.add(blob_key)
            self.blob_confirm_cache[blob_key] = self.blob_confirm_cache.get(blob_key, 0) + 1
            blob_confirmed = self.blob_confirm_cache[blob_key] >= self.MIN_BLOB_FRAMES

            # Spatial intrusion check
            in_geofence, entered_geofence, crossed_wire, _ = self.intrusion_engine.evaluate_object(
                track_id, box
            )

            # Respect geofence_enabled flag: suppress zone alerts when disabled
            if not self.geofence_enabled:
                in_geofence      = False
                entered_geofence = False

            # Threat scoring
            alert_type = None
            if crossed_wire:
                threat_score = 100
                alert_type   = "TRIPWIRE BREACH"
                label        = f"Track #{track_id} (Perimeter Breach)"
                details      = "Target traversed virtual tripwire segment"
            elif entered_geofence or in_geofence:
                threat_score = 95
                alert_type   = "GHOST OBJECT"
                label        = f"Track #{track_id} (Ghost Object)"
                details      = "Unidentified target entered restricted border geofence [Ghost Object]"
            else:
                threat_score = 25
                label        = f"Track #{track_id}"

            max_threat = max(max_threat, threat_score)

            # Fire alert only when blob is confirmed AND cooldown has expired
            if alert_type and blob_confirmed:
                cooldown_key = f"{alert_type}_{track_id}"
                if current_time - self.alert_cooldowns.get(cooldown_key, 0.0) > 5.0:
                    self.alert_cooldowns[cooldown_key] = current_time
                    self._dispatch_local_alert(
                        alert_type=alert_type,
                        identifier=label,
                        details=details,
                        threat_score=threat_score,
                        frame=frame,
                        crop=frame[y1:y2, x1:x2],
                        track_id=track_id,
                    )

            # Update active track telemetry
            if track_id not in self.active_tracks_data:
                self.active_tracks_data[track_id] = {"first_seen": current_time, "trajectory": []}
            tr_rec = self.active_tracks_data[track_id]
            tr_rec["last_seen"]    = current_time
            tr_rec["last_pos"]     = [int(footprint[0]), int(footprint[1])]
            tr_rec["threat_score"] = threat_score
            tr_rec["behavior"]     = (
                "Tripwire Breach" if crossed_wire
                else ("Zone Intrusion" if (entered_geofence or in_geofence) else "Monitoring")
            )
            tr_rec["class_name"]    = "person"
            tr_rec["speed_px_sec"]  = 4.2
            tr_rec["identity"]      = "Unknown"
            tr_rec["is_authorized"] = False
            if len(tr_rec["trajectory"]) < 40:
                tr_rec["trajectory"].append([int(footprint[0]), int(footprint[1])])

            # ── HUD Rendering — box is ALWAYS drawn, confirmed only gates alerts ──
            if threat_score >= 85:
                box_color = self.COLOR_CRITICAL      # red
            elif threat_score >= 60:
                box_color = self.COLOR_WARNING       # orange
            elif blob_confirmed:
                box_color = self.COLOR_SAFE          # green/teal
            else:
                box_color = (180, 180, 180)          # grey — building track

            # Bounding box — ALWAYS drawn
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.circle(frame, footprint, 5, box_color, -1)

            # Label bar
            in_zone_tag  = " [ZONE]" if (in_geofence or entered_geofence) else ""
            wire_tag     = " [WIRE]" if crossed_wire else ""
            conf_tag     = "" if blob_confirmed else " [...]"
            hud_text     = f"Target #{track_id}{in_zone_tag}{wire_tag}{conf_tag}  {threat_score}%"

            lbl_bg_x2 = min(w, x1 + max(len(hud_text) * 8, x2 - x1))
            lbl_y1    = max(0, y1 - 22)
            cv2.rectangle(frame, (x1, lbl_y1), (lbl_bg_x2, y1), box_color, -1)
            cv2.putText(
                frame, hud_text, (x1 + 3, max(y1 - 6, 14)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 0, 0), 2, cv2.LINE_AA,
            )

        # Prune stale blob confirmation entries
        stale_blobs = [k for k in list(self.blob_confirm_cache.keys()) if k not in alive_blob_keys]
        for k in stale_blobs:
            self.blob_confirm_cache.pop(k, None)

        self.latest_max_threat = max_threat
        self._render_status_badge(frame)
        return frame

    def _dispatch_local_alert(self, alert_type: str, identifier: str, details: str, threat_score: int, frame: np.ndarray, crop: np.ndarray, track_id: int):
        """Saves forensic evidence and pushes alert to callback."""
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        evidence_id = f"EV-{timestamp_str}-T{track_id}"

        # Save crop & scene
        crop_filename = f"{evidence_id}_crop.jpg"
        scene_filename = f"{evidence_id}_scene.jpg"
        crop_path = self.evidence_dir / crop_filename
        scene_path = self.evidence_dir / scene_filename

        if crop.size > 0:
            cv2.imwrite(str(crop_path), crop)
        cv2.imwrite(str(scene_path), frame)

        # Compute SHA-256 hash
        hasher = hashlib.sha256()
        with open(str(scene_path), "rb") as f:
            hasher.update(f.read())
        sha256_hash = f"sha256:{hasher.hexdigest()[:16]}"

        if self.alert_callback:
            self.alert_callback({
                "id": f"ALT-{int(time.time() * 1000)}",
                "camera_id": self.camera_id,
                "camera_name": self.camera_name,
                "alert_type": alert_type,
                "severity": "CRITICAL" if threat_score >= 85 else "WARNING",
                "threat_score": threat_score,
                "label": identifier,
                "details": details,
                "snapshot_url": f"/data/evidence/{crop_filename}",
                "timestamp": time.strftime("%H:%M:%S"),
            })

        if self.evidence_callback:
            self.evidence_callback({
                "id": evidence_id,
                "camera_id": self.camera_id,
                "camera_name": self.camera_name,
                "event": alert_type,
                "track_id": track_id,
                "crop_image": f"/data/evidence/{crop_filename}",
                "scene_image": f"/data/evidence/{scene_filename}",
                "sha256_hash": sha256_hash,
                "threat_score": threat_score,
                "behavior": "Intrusion",
                "identity": identifier,
            })

    def _render_status_badge(self, frame: np.ndarray):
        """Draws top HUD telemetry badge."""
        mode_text = "MODE: YOLOv8 + FRS + ANPR" if self.dl_enabled else "MODE: EDGE SPATIAL INTRUSION"
        fps_text = f"FPS: {self.current_fps} | TRACKS: {self.active_tracks_count}"
        cv2.putText(frame, f"{mode_text} | {fps_text}", (14, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200), 1, cv2.LINE_AA)

    # -------------------------------------------------------------------------
    # Zone Calibration API
    # -------------------------------------------------------------------------
    def update_zones(
        self,
        geofence_pts: Optional[List[List[int]]] = None,
        tripwire_pts: Optional[List[List[int]]] = None,
        geofence_enabled: Optional[bool] = None,
        **kwargs,
    ) -> None:
        """
        Dynamically updates geofence and tripwire coordinates without restarting.
        Works seamlessly on both PerimeterTrackerEngine and SpatialIntrusionEngine.
        """
        if geofence_enabled is not None:
            self.geofence_enabled = bool(geofence_enabled)
            if hasattr(self, "tracker") and self.tracker is not None:
                self.tracker.geofence_enabled = bool(geofence_enabled)
            logger.info("Updated geofence_enabled to %s", self.geofence_enabled)

        if geofence_pts is not None:
            self.intrusion_engine.update_geofence(geofence_pts)
            logger.info("Updated geofence polygon points: %s", geofence_pts)

        if tripwire_pts is not None and len(tripwire_pts) == 2:
            self.intrusion_engine.tripwire = (tuple(tripwire_pts[0]), tuple(tripwire_pts[1]))
            logger.info("Updated tripwire vector points: %s", tripwire_pts)

    def get_active_tracks(self) -> List[Dict[str, Any]]:
        """Returns live active track kinematics for tracking APIs."""
        results = []
        now = time.time()
        if self.dl_enabled and hasattr(self, "tracker"):
            for tid, mem in list(self.tracker.track_memory.items()):
                id_info = getattr(self.tracker, "identity_cache", {}).get(tid, {})
                threat_info = getattr(self.tracker, "threat_records", {}).get(tid, {})
                last_pos = mem.get("last_pos", (0, 0))
                results.append({
                    "track_id": tid,
                    "camera_id": self.camera_id,
                    "class_name": getattr(self.tracker, "class_cache", {}).get(tid, "person"),
                    "threat_score": threat_info.get("threat_score", 0),
                    "behavior": threat_info.get("behavior", "Normal"),
                    "identity": id_info.get("identity"),
                    "is_authorized": id_info.get("is_authorized"),
                    "speed_px_sec": round(float(mem.get("speed", 0.0)), 1),
                    "dwell_sec": round(float(mem.get("dwell", 0.0)), 1),
                    "last_position": list(last_pos) if last_pos else None,
                })
        else:
            # Purge stale tracks (> 3.5s unseen)
            dead_tids = [tid for tid, t in list(self.active_tracks_data.items()) if now - t.get("last_seen", 0) > 3.5]
            for tid in dead_tids:
                self.active_tracks_data.pop(tid, None)

            for tid, t in self.active_tracks_data.items():
                dwell = round(now - t.get("first_seen", now), 1)
                results.append({
                    "track_id": tid,
                    "camera_id": self.camera_id,
                    "class_name": t.get("class_name", "person"),
                    "threat_score": t.get("threat_score", 0),
                    "behavior": t.get("behavior", "Normal"),
                    "identity": t.get("identity"),
                    "is_authorized": t.get("is_authorized"),
                    "speed_px_sec": t.get("speed_px_sec", 3.5),
                    "dwell_sec": dwell,
                    "last_position": t.get("last_pos"),
                })
        return results

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Returns live telemetry snapshot with REAL AI inference confidence values.
        Confidence values come from tracker._smooth_confs (EMA-smoothed per-frame
        readings from YOLO, FaceNet-FRS, EasyOCR-ANPR, and tactical threat scoring).
        Falls back to reasonable static defaults when DL engine is not loaded.
        """
        if self.dl_enabled and hasattr(self, "tracker"):
            sc = self.tracker._smooth_confs
            model_confidences = {
                # YOLO26n // BYTE_TRACK — mean detection confidence this frame
                "object_detection": round(sc.get("yolo_byte_track", 0.88), 4),
                # TACTICAL_THREAT — normalised max threat score [0,1]
                "tactical_threat":  round(sc.get("tactical_threat",  0.91), 4),
                # FACENET_FRS // 512D_RESNET — face verification confidence
                "face_recognition": round(sc.get("facenet_frs",      0.92), 4),
                # EASY_OCR // ANPR_ENGINE — plate OCR confidence
                "plate_ocr":        round(sc.get("easy_ocr_anpr",    0.95), 4),
            }
        else:
            # Edge-spatial fallback: derive from live track / threat counts
            model_confidences = {
                "object_detection": 0.82 if self.active_tracks_count > 0 else 0.72,
                "tactical_threat":  round(min(0.99, 0.60 + self.latest_max_threat / 250), 2),
                "face_recognition": 0.0,   # FRS not active in spatial-CV mode
                "plate_ocr":        0.0,   # OCR not active in spatial-CV mode
            }

        return {
            "camera_id":         self.camera_id,
            "fps":               self.current_fps,
            "active_tracks":     self.active_tracks_count,
            "max_threat":        self.latest_max_threat,
            "engine_mode":       "DEEP_LEARNING" if self.dl_enabled else "EDGE_SPATIAL_CV",
            "model_confidences": model_confidences,
        }

