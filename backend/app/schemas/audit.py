from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    ip_address: Optional[str] = None
    metadata_json: str
    created_at: datetime
