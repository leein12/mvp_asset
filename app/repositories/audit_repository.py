from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditLog)

    def list_filtered(
        self,
        entity_type: str | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[AuditLog]:
        stmt = select(AuditLog)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if date_from:
            stmt = stmt.where(AuditLog.timestamp >= date_from)
        if date_to:
            stmt = stmt.where(AuditLog.timestamp <= date_to)
        stmt = stmt.order_by(AuditLog.timestamp.desc())
        return list(self.session.scalars(stmt).all())
