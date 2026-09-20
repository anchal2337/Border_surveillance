from typing import Optional
from pydantic import BaseModel, ConfigDict


class StorageHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_disk_bytes: int
    free_disk_bytes: int
    used_disk_bytes: int
    evidence_dir_bytes: int
    crossings_dir_bytes: int
    database_bytes: int
    evidence_count: int
    crossings_count: int
    alerts_count: int
    is_healthy: bool
    status_message: str


class PruneRequest(BaseModel):
    max_age_days: Optional[int] = 30
    max_storage_mb: Optional[int] = None


class PruneResponse(BaseModel):
    files_removed: int
    bytes_reclaimed: int
    status: str
    message: str
