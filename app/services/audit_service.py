from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = AuditRepository(session)

    def log(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        before_data: dict | None,
        after_data: dict | None,
        changed_fields: list[str] | None,
    ) -> AuditLog:
        log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_data=before_data,
            after_data=after_data,
            changed_fields=changed_fields,
        )
        self.repo.add(log)
        return log

    def list_logs(
        self,
        entity_type: str | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[AuditLog]:
        return self.repo.list_filtered(entity_type, action, date_from, date_to)
