import time
import threading
from typing import Optional, Generator, Tuple
import cv2
import numpy as np

class StreamBroadcaster:
    """
    Thread-safe, zero-lag frame distributor multiplexing a single camera feed
    to multiple concurrent HTTP streaming clients without duplicate AI inference.
    Uses a threading condition variable so client threads wait efficiently for new frames.
    """

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self._lock = threading.Lock()
        self._new_frame_cond = threading.Condition(self._lock)
        
        self._latest_jpeg: Optional[bytes] = None
        self._latest_frame_num: int = 0
        self._latest_timestamp: float = 0.0
        self._width: int = 1920
        self._height: int = 1080
        self._fps: float = 0.0
        self._is_active: bool = True

    def publish_frame(self, frame: np.ndarray, fps: float = 0.0) -> None:
        """
        Encodes and broadcasts a freshly processed frame to all waiting client streams.
        """
        if frame is None or frame.size == 0:
            return

        h, w = frame.shape[:2]
        # High-efficiency JPEG compression (Quality 82 provides crisp tactical HUD with small bandwidth)
        success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        if not success:
            return

        jpeg_bytes = buffer.tobytes()

        with self._new_frame_cond:
            self._latest_jpeg = jpeg_bytes
            self._latest_frame_num += 1
            self._latest_timestamp = time.time()
            self._width = w
            self._height = h
            self._fps = fps
            self._new_frame_cond.notify_all()

    def get_latest_snapshot(self) -> Optional[bytes]:
        """Returns the single latest JPEG frame bytes immediately."""
        with self._lock:
            return self._latest_jpeg

    def get_metadata(self) -> dict:
        """Returns streaming metadata."""
        with self._lock:
            return {
                "camera_id": self.camera_id,
                "frame_number": self._latest_frame_num,
                "fps": self._fps,
                "resolution": f"{self._width}x{self._height}",
                "timestamp": self._latest_timestamp,
                "is_active": self._is_active,
            }

    def generate_mjpeg_stream(self, timeout: float = 2.0) -> Generator[bytes, None, None]:
        """
        Generator producing the multipart/x-mixed-replace MJPEG stream for browsers.
        Yields immediately if a frame exists, then waits for fresh frames.
        """
        last_yielded_frame = -1

        while self._is_active:
            with self._new_frame_cond:
                # Wait until a fresh frame arrives if current has already been sent
                if self._latest_jpeg is None or self._latest_frame_num == last_yielded_frame:
                    signaled = self._new_frame_cond.wait(timeout=timeout)
                    if not signaled and self._latest_jpeg is None:
                        # Still no frame published
                        continue

                if not self._is_active:
                    break

                if self._latest_jpeg is None:
                    continue

                frame_bytes = self._latest_jpeg
                last_yielded_frame = self._latest_frame_num

            # Yield multipart boundary frame
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(frame_bytes)).encode("ascii") + b"\r\n\r\n"
                + frame_bytes + b"\r\n"
            )

    def close(self) -> None:
        """Closes broadcaster and wakes all waiting client streams."""
        with self._new_frame_cond:
            self._is_active = False
            self._new_frame_cond.notify_all()
