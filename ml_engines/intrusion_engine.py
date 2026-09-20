from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Any, Set
import numpy as np
import cv2


class SpatialIntrusionEngine:
    """
    Deterministic spatial analysis engine for border perimeter protection.
    Provides runtime geofencing, virtual tripwires, and trajectory tracking
    without neural network latency overhead.
    """

    def __init__(
        self,
        default_tripwire: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        default_geofence: Optional[List[Tuple[int, int]]] = None,
    ):
        # Virtual tripwire: ((x1, y1), (x2, y2))
        self.tripwire: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = default_tripwire

        # Dynamic Geofence: OpenCV-compatible polygon (N, 1, 2)
        self.geofence_polygon: Optional[np.ndarray] = None
        if default_geofence:
            self.update_geofence(default_geofence)

        # Track history cache: {track_id: {'prev_footprint': (x, y), 'in_geofence': bool, 'last_seen': float}}
        self.track_history: Dict[int, Dict[str, Any]] = {}

        # Default normalized geometry fallback for initial camera view (1080x720 baseline)
        self._normalized_tripwire = ((0.10, 0.65), (0.90, 0.65))
        self._normalized_geofence = [
            (0.15, 0.35),
            (0.85, 0.35),
            (0.95, 0.85),
            (0.05, 0.85),
        ]
        self._last_frame_shape: Optional[Tuple[int, int]] = None

    # -------------------------------------------------------------------------
    # Footprint Extraction
    # -------------------------------------------------------------------------
    @staticmethod
    def get_footprint(bbox: Tuple[int, int, int, int] | List[int] | np.ndarray) -> Tuple[int, int]:
        """
        Extract the bottom-center coordinate of a bounding box.
        This represents the physical contact point where the object touches the ground plane.

        Args:
            bbox: [x1, y1, x2, y2] bounding box coordinates.

        Returns:
            (footprint_x, footprint_y) as integer pixel coordinates.
        """
        x1, y1, x2, y2 = bbox
        footprint_x = int((x1 + x2) / 2)
        footprint_y = int(y2)
        return footprint_x, footprint_y

    # -------------------------------------------------------------------------
    # Dynamic Geofencing
    # -------------------------------------------------------------------------
    def update_geofence(self, polygon_points: List[Tuple[int, int]] | np.ndarray) -> None:
        """
        Dynamically update the geofence polygon boundary at runtime.

        Args:
            polygon_points: Sequence of (x, y) vertices defining the closed polygon.
        """
        if polygon_points is None or len(polygon_points) < 3:
            self.geofence_polygon = None
            return

        pts = np.array(polygon_points, dtype=np.int32)
        if pts.ndim == 2:
            pts = pts.reshape((-1, 1, 2))
        self.geofence_polygon = pts

    def is_inside_geofence(self, point: Tuple[int, int]) -> bool:
        """
        Deterministically evaluates if a 2D coordinate lies within the geofence.

        Uses cv2.pointPolygonTest:
          > 0: Inside polygon
          = 0: On polygon boundary
          < 0: Outside polygon

        Args:
            point: (x, y) coordinate.

        Returns:
            True if point is strictly inside or on the boundary, False otherwise.
        """
        if self.geofence_polygon is None or len(self.geofence_polygon) < 3:
            return False

        pt = (float(point[0]), float(point[1]))
        return cv2.pointPolygonTest(self.geofence_polygon, pt, measureDist=False) >= 0

    # -------------------------------------------------------------------------
    # Virtual Tripwire (Counter-Clockwise Cross-Product Math)
    # -------------------------------------------------------------------------
    def update_tripwire(self, start: Tuple[int, int], end: Tuple[int, int]) -> None:
        """
        Dynamically update the virtual tripwire coordinates at runtime.

        Args:
            start: (x1, y1) start vertex of the tripwire line segment.
            end:   (x2, y2) end vertex of the tripwire line segment.
        """
        self.tripwire = ((int(start[0]), int(start[1])), (int(end[0]), int(end[1])))

    @staticmethod
    def _ccw(
        A: Tuple[int, int] | Tuple[float, float],
        B: Tuple[int, int] | Tuple[float, float],
        C: Tuple[int, int] | Tuple[float, float],
    ) -> bool:
        """
        Determines the orientation of the triplet (A, B, C).
        Evaluates whether traversing A -> B -> C forms a counter-clockwise turn
        using the 2D cross-product formula:
            (Cy - Ay) * (Bx - Ax) > (By - Ay) * (Cx - Ax)
        """
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    def check_tripwire_crossing(
        self,
        prev_point: Tuple[int, int],
        curr_point: Tuple[int, int],
    ) -> bool:
        """
        Determines if the trajectory segment between prev_point and curr_point
        intersects the tripwire line segment (C -> D) using CCW intersection math.

        Two segments AB and CD intersect if and only if:
            ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

        Args:
            prev_point: (Ax, Ay) target footprint in previous frame.
            curr_point: (Bx, By) target footprint in current frame.

        Returns:
            True if the trajectory crossed the virtual line, False otherwise.
        """
        if not self.tripwire or len(self.tripwire) != 2:
            return False

        A, B = prev_point, curr_point
        C, D = self.tripwire

        # Avoid redundant calculation if object is stationary
        if A == B:
            return False

        intersect = (self._ccw(A, C, D) != self._ccw(B, C, D)) and (
            self._ccw(A, B, C) != self._ccw(A, B, D)
        )
        return bool(intersect)

    # -------------------------------------------------------------------------
    # Object Spatial Lifecycle Evaluation
    # -------------------------------------------------------------------------
    def evaluate_object(
        self,
        track_id: int,
        bbox: Tuple[int, int, int, int] | List[int] | np.ndarray,
    ) -> Tuple[bool, bool, bool, Tuple[int, int]]:
        """
        Evaluate full spatial compliance for a tracked object.

        Args:
            track_id: Unique tracking identifier assigned by ByteTrack.
            bbox: Bounding box coordinates [x1, y1, x2, y2].

        Returns:
            (in_geofence, entered_geofence, crossed_tripwire, footprint)
        """
        curr_footprint = self.get_footprint(bbox)
        in_geofence = self.is_inside_geofence(curr_footprint)

        prev_entry = self.track_history.get(track_id)
        crossed_tripwire = False
        entered_geofence = False

        if prev_entry is not None:
            prev_footprint = prev_entry.get("prev_footprint")
            was_in_geofence = prev_entry.get("in_geofence", False)

            if prev_footprint and prev_footprint != curr_footprint:
                crossed_tripwire = self.check_tripwire_crossing(prev_footprint, curr_footprint)

            # Object just transitioned into the geofence from outside
            if in_geofence and not was_in_geofence:
                entered_geofence = True
        else:
            # First time detected; if already inside geofence, flag entry
            if in_geofence:
                entered_geofence = True

        # Update cache
        self.track_history[track_id] = {
            "prev_footprint": curr_footprint,
            "in_geofence": in_geofence,
        }

        return in_geofence, entered_geofence, crossed_tripwire, curr_footprint

    # -------------------------------------------------------------------------
    # Geometry Auto-Initialization & Visualization
    # -------------------------------------------------------------------------
    def ensure_default_geometry(self, frame_shape: Tuple[int, ...]) -> None:
        """
        Ensures default proportional zones are set if no custom geofence/tripwire
        has been explicitly defined by the operator.
        """
        height, width = frame_shape[:2]
        if self._last_frame_shape == (height, width):
            return

        self._last_frame_shape = (height, width)

        if self.tripwire is None:
            pt1 = (int(self._normalized_tripwire[0][0] * width), int(self._normalized_tripwire[0][1] * height))
            pt2 = (int(self._normalized_tripwire[1][0] * width), int(self._normalized_tripwire[1][1] * height))
            self.update_tripwire(pt1, pt2)

        if self.geofence_polygon is None:
            poly = [
                (int(x * width), int(y * height))
                for (x, y) in self._normalized_geofence
            ]
            self.update_geofence(poly)

    def draw_zones(self, frame: np.ndarray) -> np.ndarray:
        """
        Render spatial rules onto the video frame:
        - Geofence: Translucent polygon with solid boundary.
        - Virtual Tripwire: High-visibility dashed/solid line with end beacons.
        """
        self.ensure_default_geometry(frame.shape)

        # 1. Render Geofence
        if self.geofence_polygon is not None and len(self.geofence_polygon) >= 3:
            overlay = frame.copy()
            cv2.fillPoly(overlay, [self.geofence_polygon], color=(0, 50, 160))
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            cv2.polylines(frame, [self.geofence_polygon], isClosed=True, color=(0, 140, 255), thickness=3)

            # Draw Geofence Label with dark backing for 100% visibility
            moments = cv2.moments(self.geofence_polygon)
            if moments["m00"] != 0:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
                lbl = "RESTRICTED GEOFENCE"
                # Drop shadow outline
                cv2.putText(frame, lbl, (cx - 100, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(frame, lbl, (cx - 100, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 180, 255), 2, cv2.LINE_AA)

        # 2. Render Virtual Tripwire
        if self.tripwire is not None:
            pt1, pt2 = self.tripwire
            cv2.line(frame, pt1, pt2, color=(0, 220, 255), thickness=3)
            # End beacons
            cv2.circle(frame, pt1, radius=7, color=(0, 255, 255), thickness=-1)
            cv2.circle(frame, pt1, radius=9, color=(0, 0, 0), thickness=2)
            cv2.circle(frame, pt2, radius=7, color=(0, 255, 255), thickness=-1)
            cv2.circle(frame, pt2, radius=9, color=(0, 0, 0), thickness=2)
            mid_x = int((pt1[0] + pt2[0]) / 2)
            mid_y = int((pt1[1] + pt2[1]) / 2)
            tw_lbl = "VIRTUAL TRIPWIRE"
            # Drop shadow outline
            cv2.putText(frame, tw_lbl, (mid_x - 80, mid_y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(frame, tw_lbl, (mid_x - 80, mid_y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 255), 2, cv2.LINE_AA)

        return frame

    def draw_rules(self, frame: np.ndarray) -> np.ndarray:
        """Alias for backward-compatibility with existing pipeline calls."""
        return self.draw_zones(frame)

    def remove_missing_tracks(self, active_track_ids: set[int] | List[int]) -> None:
        """Prunes track history for stale tracks."""
        active_ids = set(active_track_ids)
        self.track_history = {
            tid: data for tid, data in self.track_history.items() if tid in active_ids
        }