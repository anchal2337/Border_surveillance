"""
PerimeterTrackerEngine — complete ML pipeline
==============================================
Pipeline per-frame:
  1. Draw geofence + tripwire zones (auto-scales to video resolution).
  2. Detect objects with YOLO (yolo26nfinal.pt) + ByteTrack.
     - Boxes are ALWAYS rendered even if ByteTrack hasn't assigned an ID yet.
  3. For each detected box:
       - PERSON  → apply CLAHE to crop → FaceRecognitionEngine
                    authorized  : GREEN box, no alert
                    unknown     : check geofence → in zone → RED + ALERT
                                                → outside  → ORANGE, no alert
       - VEHICLE → VehicleEngine / ANPR
                    whitelisted : GREEN box, no alert
                    unknown     : check geofence → in zone → RED + ALERT
                                                → outside  → ORANGE, no alert
       - OTHER   : label only, no alert
  4. Tripwire crossing ALWAYS fires an alert regardless of identity.
  5. All alerts have an 8-second per-key cooldown.
  6. New tracks require MIN_CONFIRMED_FRAMES before alerting (ghost suppression).
"""

import time
from typing import Optional, Dict, Any, List, Tuple
import cv2
import numpy as np
import os
from ultralytics import YOLO
from stable_baselines3 import DQN

from enhancement import apply_clahe
from face_engine import FaceRecognitionEngine
from vehicle_engine import VehicleEngine
from intrusion_engine import SpatialIntrusionEngine

# HUD colours
_GREEN  = (0, 220, 80)    # authorized / whitelisted
_ORANGE = (0, 165, 255)   # unknown, outside zone (watch)
_RED    = (0, 0, 255)     # unknown inside zone / breach
_GREY   = (180, 180, 180) # not yet confirmed (building track)
_WHITE  = (255, 255, 255)
_BLACK  = (0, 0, 0)


class PerimeterTrackerEngine:

    # ------------------------------------------------------------------ init --
    def __init__(
        self,
        face_engine: FaceRecognitionEngine,
        vehicle_engine: VehicleEngine,
        yolo_model_path: str = "yolo26n.pt",
        threat_model_path: str = None,
        rl_model_path: str = "models/behavioral_rl_model.zip",
    ):
        # ---------- YOLO detector -----------------------------------------------
        # Use yolo26n.pt as the primary detector model
        script_dir = os.path.dirname(os.path.abspath(__file__))
        _preferred = os.path.join(script_dir, "models", "yolo26n.pt")
        if not os.path.exists(_preferred):
            _preferred = os.path.join(script_dir, "yolo26n.pt")
        if os.path.exists(_preferred):
            yolo_model_path = _preferred
        elif not os.path.exists(yolo_model_path):
            yolo_model_path = "yolov8n.pt"   # ultimate fallback

        self.yolo = YOLO(yolo_model_path)
        # None tracks all objects so persons, vehicles, and potential ghost objects (bags, animals, equipment) are tracked
        self.target_classes = None
        # Standard vehicle classes in COCO: bicycle(1), car(2), motorcycle(3), airplane(4), bus(5), train(6), truck(7), boat(8)
        self.vehicle_classes = {1, 2, 3, 4, 5, 6, 7, 8}

        # ---------- sub-engines -------------------------------------------------
        self.face_engine    = face_engine
        self.vehicle_engine = vehicle_engine
        self.intrusion_engine = SpatialIntrusionEngine()
        self.vehicle_crossing_cooldowns: dict = {}

        # ---------- RL behavioural model ----------------------------------------
        self.rl_model_path = rl_model_path
        self.rl_active = os.path.exists(self.rl_model_path)
        if self.rl_active:
            self.rl_model = DQN.load(self.rl_model_path)

        # ---------- kinematic memory --------------------------------------------
        self.track_memory: dict = {}       # {trk_id: {first, last, pos, speed, dwell}}
        self.max_dwell_seconds   = 6.0
        self.max_speed_px_per_sec = 400.0

        # ---------- identity / threat caches ------------------------------------
        # {trk_id: {label, last_checked, authorized, is_authorized, identity}}
        self.identity_cache: dict = {}
        self.cache_timeout = 3.0           # re-run FRS/OCR every 3 s per track

        self.threat_records: dict = {}     # {trk_id: {threat_score, behavior}}
        self.class_cache:    dict = {}     # {trk_id: class_name}

        # ---------- ghost-suppression -------------------------------------------
        self.track_confirmed_frames: dict = {}
        self.MIN_CONFIRMED_FRAMES = 3      # frames before any alert is fired

        # ---------- alert store + cooldowns -------------------------------------
        self.active_alerts: list  = []
        self.alert_cooldowns: dict = {}

        # ---------- live inference confidence matrix ----------------------------
        # Updated every frame with REAL values from model inference.
        # Consumed by ai_adapter.get_telemetry() → WebSocket → frontend matrix UI.
        self._live_confs: dict = {
            "yolo_byte_track":    0.0,   # mean YOLO detection confidence this frame
            "tactical_threat":    0.0,   # max threat score normalised to [0,1]
            "facenet_frs":        0.0,   # latest FRS verification confidence
            "easy_ocr_anpr":      0.0,   # latest OCR read confidence
        }
        # Running smoothed values (EMA α=0.3) so the UI doesn't flicker
        self._smooth_confs: dict = {k: 0.88 for k in self._live_confs}
        self._EMA_ALPHA = 0.3            # smoothing factor

        # ---------- geofence toggle (frontend-controlled) -----------------------
        self.geofence_enabled: bool = True

        # ---------- stubs (overridden by ai_adapter proxy hooks) ----------------
        self.current_camera_name = "Perimeter Cam"

    def is_vehicle(self, cls_id: int, class_name: str) -> bool:
        if cls_id in self.vehicle_classes:
            return True
        c = (class_name or "").lower()
        return any(k in c for k in ("car", "truck", "bus", "motor", "bike", "cycle", "vehic", "van", "suv", "train", "boat", "auto", "jeep", "lorry"))

    def is_person(self, cls_id: int, class_name: str) -> bool:
        if cls_id == 0:
            return True
        c = (class_name or "").lower()
        return "person" in c or "pedestrian" in c or "human" in c

    # ---------------------------------------------------------- alert engine --
    def trigger_alert(
        self,
        alert_type: str,
        identifier: str,
        details: str,
        frame: Optional[np.ndarray] = None,
        crop: Optional[np.ndarray] = None,
        track_id: int = 0,
        threat_score: int = 85,
    ) -> bool:
        """Fires a deduped alert with 8-second per-key cooldown. Returns True if new."""
        now = time.time()
        key = f"{alert_type}_{identifier}"
        if now - self.alert_cooldowns.get(key, 0) > 8:
            self.alert_cooldowns[key] = now
            self.active_alerts.insert(0, {
                "id":        str(int(now * 1000)),
                "type":      alert_type,
                "label":     identifier,
                "details":   details,
                "timestamp": time.strftime("%H:%M:%S"),
            })
            self.active_alerts = self.active_alerts[:30]
            return True
        return False

    # ---------------------------------------- stubs for ai_adapter hooks -----
    def capture_investigation_evidence(self, **kwargs):
        pass

    def _save_vehicle_crossing_record(
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
        pass

    # -------------------------------------- live confidence matrix helper -----
    def _update_smooth_conf(self, key: str, new_value: float) -> None:
        """
        Exponential Moving Average update for a confidence key.
        Keeps the UI confidence matrix smooth (no frame-to-frame flicker).
        α = 0.3  →  new value contributes 30%, history 70%.
        """
        old = self._smooth_confs.get(key, new_value)
        self._smooth_confs[key] = round(
            self._EMA_ALPHA * new_value + (1 - self._EMA_ALPHA) * old, 4
        )

    # --------------------------------------------------- main frame pipeline --
    def process_frame(self, frame: np.ndarray, enable_clahe: bool = False) -> np.ndarray:
        """
        Process one video frame through the full ML pipeline.
        Bounding boxes are ALWAYS drawn even on the very first frame.
        """
        h, w = frame.shape[:2]
        curr_time = time.time()

        # ── 1. Spatial zone overlay (auto-scales to current resolution) ─────────
        frame = self.intrusion_engine.draw_zones(frame)

        # ── 2. YOLO + ByteTrack detection ───────────────────────────────────────
        results = self.yolo.track(
            source=frame,
            classes=self.target_classes,
            persist=True,
            tracker="bytetrack.yaml",
            imgsz=640,
            conf=0.10,
            verbose=False,
        )

        active_track_ids = []

        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            self._render_hud(frame, 0, 0)
            return frame

        raw_boxes  = results[0].boxes.xyxy.cpu().numpy().astype(int)
        raw_cls    = results[0].boxes.cls.cpu().numpy().astype(int)
        raw_conf   = results[0].boxes.conf.cpu().numpy()

        # ── Update YOLO live confidence (mean detection score this frame) ────────
        if len(raw_conf) > 0:
            self._update_smooth_conf("yolo_byte_track", float(raw_conf.mean()))

        # ByteTrack IDs (may be None on very first frame)
        if results[0].boxes.id is not None:
            raw_ids = results[0].boxes.id.cpu().numpy().astype(int)
        else:
            # No IDs yet — assign temporary negatives so we still render boxes
            raw_ids = np.arange(-len(raw_boxes), 0, dtype=int)

        active_track_ids = [tid for tid in raw_ids if tid >= 0]
        max_threat = 0

        for box, cls_id, trk_id, conf in zip(raw_boxes, raw_cls, raw_ids, raw_conf):
            x1 = max(0, int(box[0])); y1 = max(0, int(box[1]))
            x2 = min(w, int(box[2])); y2 = min(h, int(box[3]))
            if x2 <= x1 or y2 <= y1:
                continue

            class_name = self.yolo.names.get(cls_id, f"obj_{cls_id}")
            is_vehicle = self.is_vehicle(cls_id, class_name)
            is_person  = self.is_person(cls_id, class_name)
            is_ghost   = not (is_person or is_vehicle)

            # Cache class for telemetry API
            if trk_id >= 0:
                self.class_cache[trk_id] = class_name

            curr_x = (x1 + x2) / 2.0
            curr_y = float(y2)

            # ── Frame-confirmation counter ─────────────────────────────────────
            if trk_id >= 0:
                self.track_confirmed_frames[trk_id] = (
                    self.track_confirmed_frames.get(trk_id, 0) + 1
                )
                track_confirmed = self.track_confirmed_frames[trk_id] >= self.MIN_CONFIRMED_FRAMES
            else:
                # Untracked detection: show box immediately but don't alert
                track_confirmed = False

            # ── Spatial evaluation ─────────────────────────────────────────────
            if trk_id >= 0:
                in_geofence, entered_geofence, crossed_wire, footprint = (
                    self.intrusion_engine.evaluate_object(trk_id, box)
                )
            else:
                # Temporary ID — skip stateful spatial eval
                footprint = (int(curr_x), int(curr_y))
                in_geofence = entered_geofence = crossed_wire = False

            # Respect live geofence toggle from frontend
            if not self.geofence_enabled:
                in_geofence      = False
                entered_geofence = False

            in_zone = in_geofence or entered_geofence
            crossed_fence = crossed_wire or entered_geofence

            # Always extract bounding box crop for forensic evidence, FRS, and ANPR
            crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)].copy()

            # ── Identity check (FRS / ANPR) with throttle cache ────────────────
            cached = self.identity_cache.get(trk_id) if trk_id >= 0 else None
            needs_scan = (
                cached is None
                or (curr_time - cached["last_checked"] > self.cache_timeout)
            )

            # If vehicle is crossing fence or tripwire and plate not yet confirmed, force scan
            if is_vehicle and (in_zone or crossed_wire) and (cached is None or cached.get("label") in ("No Plate", "Scanning...", None) or not cached.get("authorized")):
                needs_scan = True

            id_label    = "Scanning..."
            authorized  = False   # face recognized / plate whitelisted
            _pconf      = 0.0

            if needs_scan:
                if is_person and crop.size > 0:
                    # Apply CLAHE only on the person crop before FRS
                    enhanced_crop = apply_clahe(crop)
                    name, desig, auth, _fconf = self.face_engine.verify_crop(enhanced_crop)
                    authorized = bool(auth)
                    id_label   = name if authorized else "Unknown Person"
                    # ► Push real FRS confidence to live matrix ◄
                    self._update_smooth_conf("facenet_frs", float(_fconf))

                elif is_vehicle and crop.size > 0:
                    plate, whitelisted, _pconf = self.vehicle_engine.verify_plate(crop)
                    authorized = bool(whitelisted)
                    if plate:
                        id_label = plate
                        # ► Push real OCR/ANPR confidence to live matrix ◄
                        self._update_smooth_conf("easy_ocr_anpr", float(_pconf))
                    else:
                        id_label = "No Plate"

                else:
                    id_label   = class_name
                    authorized = False

                if trk_id >= 0:
                    self.identity_cache[trk_id] = {
                        "label":        id_label,
                        "last_checked": curr_time,
                        "authorized":   authorized,
                        "identity":     id_label,
                        "is_authorized": authorized,
                        "pconf":        float(_pconf),
                    }
            else:
                id_label   = cached["label"]
                authorized = cached.get("authorized", False)
                _pconf     = cached.get("pconf", 0.0)

            # ── Store Vehicle Crossing when traversing fence or tripwire ───────
            # User requirement: "if vehical then i want its snap shot if it cross or enters the geofencing in vehical_crossing"
            if is_vehicle and (in_zone or crossed_wire) and crop.size > 0:
                crossing_cooldown_key = trk_id if trk_id >= 0 else 0
                if curr_time - self.vehicle_crossing_cooldowns.get(crossing_cooldown_key, 0.0) > 6.0:
                    self.vehicle_crossing_cooldowns[crossing_cooldown_key] = curr_time
                    crossing_details = (
                        f"Crossed virtual perimeter trip line ({class_name})"
                        if crossed_wire
                        else f"Entered restricted perimeter fence ({class_name})"
                    )
                    # Apply CLAHE enhancement to crop for superior license plate readability and forensic clarity
                    clahe_crop = apply_clahe(crop)
                    final_crop = clahe_crop if (clahe_crop is not None and clahe_crop.size > 0) else crop
                    self._save_vehicle_crossing_record(
                        plate=id_label if (id_label and id_label != "No Plate") else f"VEH-{trk_id}",
                        vehicle_type=class_name,
                        track_id=int(trk_id),
                        confidence=float(_pconf if id_label != "No Plate" else conf),
                        is_whitelisted=authorized,
                        image_path="",
                        details=crossing_details,
                        crop=final_crop,
                        frame=frame,
                    )

            # ── Alert & colour decision ────────────────────────────────────────
            #
            # RULE:
            #   authorized (known person / whitelisted vehicle)
            #     → GREEN box, NEVER alert, even if inside geofence
            #   unknown + in_zone
            #     → RED box, ALERT (if track confirmed)
            #   unknown + outside zone
            #     → ORANGE box, no alert
            #   tripwire crossed
            #     → RED box, ALERT always (even authorized)
            #
            threat_score    = 0
            behavior_label  = "NORMAL"
            color           = _GREY    # default until confirmed

            if not track_confirmed:
                # Still building confidence — grey box, no alert, no colour logic
                color = _GREY
            elif crossed_wire:
                # Tripwire breach: alert regardless of identity
                color          = _RED
                threat_score   = 100
                if is_ghost:
                    behavior_label = f"GHOST OBJECT TRIPWIRE BREACH ({class_name.upper()})"
                    alert_type     = "GHOST OBJECT"
                    target_label   = f"#{trk_id} Ghost Object ({class_name.upper()})"
                elif is_vehicle:
                    behavior_label = "VEHICLE TRIPWIRE BREACH"
                    alert_type     = "TRIPWIRE BREACH"
                    target_label   = f"#{trk_id} {id_label} [{class_name.upper()}]"
                else:
                    behavior_label = "PERIMETER BREACH"
                    alert_type     = "TRIPWIRE BREACH"
                    target_label   = f"#{trk_id} {id_label}"

                self.trigger_alert(
                    alert_type,
                    target_label,
                    f"Target traversed virtual perimeter tripwire ({class_name})",
                    frame=frame,
                    crop=crop,
                    track_id=int(trk_id),
                    threat_score=100,
                )
            elif authorized:
                # Known / whitelisted → always safe
                color          = _GREEN
                threat_score   = 0
                behavior_label = "AUTHORIZED"
            elif in_zone:
                # Target inside restricted geofence
                color = _RED
                if is_ghost:
                    # User requirement: "ghost objects will be other than person and vehicals if any object is unknown and enters the geofence then create alert ghost object"
                    threat_score   = 95
                    behavior_label = f"GHOST OBJECT IN ZONE ({class_name.upper()})"
                    self.trigger_alert(
                        "GHOST OBJECT",
                        f"#{trk_id} Ghost Object ({class_name.upper()})",
                        f"Unidentified non-human/non-vehicle object detected inside restricted geofence [Ghost Object: {class_name.upper()}]",
                        frame=frame,
                        crop=crop,
                        track_id=int(trk_id),
                        threat_score=95,
                    )
                elif is_person:
                    # Unrecognized person inside restricted geofence
                    threat_score   = 90
                    behavior_label = "UNAUTHORIZED PERSON IN ZONE"
                    self.trigger_alert(
                        "INTRUSION ALERT",
                        f"#{trk_id} Unknown Person",
                        "Unrecognized person detected inside restricted geofence",
                        frame=frame,
                        crop=crop,
                        track_id=int(trk_id),
                        threat_score=90,
                    )
                else:
                    # Unregistered vehicle inside restricted geofence
                    threat_score   = 85
                    behavior_label = f"UNREGISTERED {class_name.upper()} IN ZONE"
                    self.trigger_alert(
                        "VEHICLE THREAT",
                        f"#{trk_id} {id_label} [{class_name.upper()}]",
                        f"Unregistered {class_name} detected inside restricted geofence",
                        frame=frame,
                        crop=crop,
                        track_id=int(trk_id),
                        threat_score=85,
                    )
            else:
                # Outside restricted zone → watch
                if is_ghost:
                    color          = _GREY
                    threat_score   = 10
                    behavior_label = f"{class_name.upper()} — MONITORING"
                elif is_person:
                    color          = _ORANGE
                    threat_score   = 25
                    behavior_label = "UNKNOWN PERSON — MONITORING"
                else:
                    color          = _ORANGE
                    threat_score   = 25
                    behavior_label = f"{class_name.upper()} — MONITORING"

            max_threat = max(max_threat, threat_score)

            # Store for external telemetry API
            if trk_id >= 0:
                self.threat_records[trk_id] = {
                    "threat_score": threat_score,
                    "behavior":     behavior_label,
                }
                # Update kinematic memory for all tracked objects
                if trk_id not in self.track_memory:
                    self.track_memory[trk_id] = {
                        "first": curr_time, "last": curr_time,
                        "pos":   (curr_x, curr_y),
                        "speed": 0.0, "dwell": 0.0,
                    }
                else:
                    prev = self.track_memory[trk_id]
                    dt   = curr_time - prev["last"]
                    spd  = (
                        np.sqrt((curr_x - prev["pos"][0])**2 + (curr_y - prev["pos"][1])**2) / dt
                        if dt > 0 else 0.0
                    )
                    self.track_memory[trk_id].update({
                        "last":  curr_time,
                        "pos":   (curr_x, curr_y),
                        "speed": spd,
                        "dwell": curr_time - self.track_memory[trk_id]["first"],
                    })

            # ── HUD rendering ──────────────────────────────────────────────────
            # Always draw the bounding box (prominent 3px border for 1080p)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

            # Footprint dot (only for tracked, confirmed objects)
            if trk_id >= 0 and track_confirmed:
                cv2.circle(frame, footprint, 6, color, -1)

            # Label bar (high-visibility contrast)
            tid_str   = f"#{trk_id}" if trk_id >= 0 else "#?"
            auth_tag  = " [AUTH]" if authorized else ""
            zone_tag  = " [ZONE]" if (in_zone and track_confirmed) else ""
            conf_tag  = "" if track_confirmed else " [...]"

            if is_ghost and in_zone:
                obj_label = f"GHOST OBJECT [{class_name.upper()}]"
            elif is_vehicle:
                plate_str = id_label if (id_label and id_label != "No Plate") else "No Plate"
                obj_label = f"{plate_str} [{class_name.upper()}]"
            elif is_person:
                obj_label = id_label
            else:
                obj_label = class_name.upper()

            label_str = f"{tid_str} {obj_label}{auth_tag}{zone_tag}{conf_tag}  {int(conf*100)}%"

            txt_w = max(len(label_str) * 9 + 12, x2 - x1)
            # Position label inside box if near top of frame, else above box
            if y1 > 40:
                lbl_y1 = y1 - 28
                lbl_y2 = y1
                txt_y  = y1 - 8
            else:
                lbl_y1 = y1
                lbl_y2 = y1 + 28
                txt_y  = y1 + 20

            cv2.rectangle(frame, (x1, lbl_y1), (x1 + txt_w, lbl_y2), color, -1)
            cv2.putText(
                frame, label_str,
                (x1 + 6, txt_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, _BLACK, 2, cv2.LINE_AA,
            )

            # Threat badge (right side) if alerting
            if threat_score >= 85 and track_confirmed:
                badge = f"THREAT {threat_score}%"
                cv2.putText(
                    frame, badge,
                    (x2 - len(badge) * 10, y1 + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, _RED, 2, cv2.LINE_AA,
                )

        # ── Memory cleanup ──────────────────────────────────────────────────────
        stale = [
            t for t, d in self.track_memory.items()
            if t not in active_track_ids and (curr_time - d["last"]) > 2.0
        ]
        for t in stale:
            self.track_memory.pop(t, None)
            self.identity_cache.pop(t, None)
            self.threat_records.pop(t, None)
            self.class_cache.pop(t, None)
            self.track_confirmed_frames.pop(t, None)

        self.intrusion_engine.remove_missing_tracks(active_track_ids)

        # ── Update tactical threat confidence from this frame's max score ────────
        # Normalise 0-100 threat score to [0,1] for the confidence matrix.
        self._update_smooth_conf("tactical_threat", max_threat / 100.0)

        # ── Status HUD ─────────────────────────────────────────────────────────
        self._render_hud(frame, len(active_track_ids), max_threat)
        return frame

    # --------------------------------------------------------- HUD helpers ---
    def _render_hud(self, frame: np.ndarray, num_tracks: int, max_threat: int) -> None:
        """
        Tactical telemetry status pill.
        Placed at y=52 to y=82 so it sits clearly below the browser's top header bar
        and is 100% visible against any background with a dark contrast pill.
        """
        geo_state = "ARMED" if self.geofence_enabled else "STANDBY"
        hud_text = (
            f"YOLO26n-ByteTrack  |  TARGETS: {num_tracks}  |  "
            f"MAX THREAT: {max_threat}%  |  GEOFENCE: {geo_state}"
        )
        pill_w = len(hud_text) * 9 + 24
        # Dark tactical backdrop pill
        cv2.rectangle(frame, (16, 50), (16 + pill_w, 82), (12, 16, 20), -1)
        cv2.rectangle(frame, (16, 50), (16 + pill_w, 82), (0, 200, 160), 1)
        cv2.putText(
            frame, hud_text, (26, 72),
            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 200), 1, cv2.LINE_AA,
        )