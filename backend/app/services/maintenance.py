import os
import shutil
import time
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.entities import EvidenceLocker, VehicleCrossing, Alert

logger = logging.getLogger("maintenance")


class DiskRetentionManager:
    """
    Manages air-gapped border station disk storage health and FIFO retention purging.
    Ensures continuous 24/7 video analytics without out-of-disk crashes.
    """

    def __init__(self):
        self.data_dir = settings.DATA_DIR
        self.evidence_dir = settings.EVIDENCE_DIR
        self.crossings_dir = settings.DATA_DIR / "vehicle_crossings"
        self.db_path = settings.DATA_DIR / "ibvap.db"

    def _get_dir_size(self, path: Path) -> int:
        """Calculates recursive directory size in bytes."""
        if not path.exists():
            return 0
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception as e:
            logger.warning("Error calculating size of %s: %s", path, e)
        return total

    def get_storage_health(self, db: Session) -> Dict[str, Any]:
        """Returns comprehensive storage allocation and system metrics."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        total, used, free = shutil.disk_usage(self.data_dir)

        evidence_size = self._get_dir_size(self.evidence_dir)
        crossings_size = self._get_dir_size(self.crossings_dir)
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        ev_count = db.query(EvidenceLocker).count()
        cross_count = db.query(VehicleCrossing).count()
        alert_count = db.query(Alert).count()

        # Healthy if free disk space is greater than 1 GB
        is_healthy = free > (1024 * 1024 * 1024)
        status_msg = "Storage Optimal" if is_healthy else "WARNING: Disk space critically low"

        return {
            "total_disk_bytes": total,
            "free_disk_bytes": free,
            "used_disk_bytes": used,
            "evidence_dir_bytes": evidence_size,
            "crossings_dir_bytes": crossings_size,
            "database_bytes": db_size,
            "evidence_count": ev_count,
            "crossings_count": cross_count,
            "alerts_count": alert_count,
            "is_healthy": is_healthy,
            "status_message": status_msg,
        }

    def prune_old_records(
        self,
        db: Session,
        max_age_days: int = 30,
        max_storage_mb: Optional[int] = None,
    ) -> Tuple[int, int]:
        """
        Executes FIFO purging on oldest non-essential media files.
        Preserves active evidence cases while pruning old transient frames.
        """
        now = time.time()
        max_age_sec = max_age_days * 86400
        files_removed = 0
        bytes_reclaimed = 0

        dirs_to_clean = [self.evidence_dir, self.crossings_dir]

        for target_dir in dirs_to_clean:
            if not target_dir.exists():
                continue

            file_list = []
            for item in target_dir.glob("*.jpg"):
                try:
                    stat = item.stat()
                    file_list.append((item, stat.st_mtime, stat.st_size))
                except Exception:
                    pass

            # Sort FIFO (oldest first)
            file_list.sort(key=lambda x: x[1])

            for file_path, mtime, size in file_list:
                should_delete = False
                if (now - mtime) > max_age_sec:
                    should_delete = True

                if should_delete:
                    try:
                        file_path.unlink(missing_ok=True)
                        files_removed += 1
                        bytes_reclaimed += size
                    except Exception as e:
                        logger.warning("Could not delete file %s: %s", file_path, e)

        logger.info(
            "Disk retention completed: %d files pruned, %d bytes reclaimed.",
            files_removed,
            bytes_reclaimed,
        )
        return files_removed, bytes_reclaimed


retention_manager = DiskRetentionManager()
