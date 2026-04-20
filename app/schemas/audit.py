from datetime import datetime

from app.schemas.common import ORMModel


class AuditRead(ORMModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    before_data: dict | None
    after_data: dict | None
    changed_fields: list[str] | None
    timestamp: datetime
