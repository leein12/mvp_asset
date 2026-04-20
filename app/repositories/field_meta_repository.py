from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import FieldMeta
from app.repositories.base import BaseRepository


class FieldMetaRepository(BaseRepository[FieldMeta]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, FieldMeta)

    def list_by_entity(self, entity_type: str, *, include_unused: bool = False) -> list[FieldMeta]:
        stmt = select(FieldMeta).where(FieldMeta.entity_type == entity_type.upper())
        if not include_unused:
            stmt = stmt.where(FieldMeta.in_use.is_(True))
        stmt = stmt.order_by(FieldMeta.field_key.asc())
        return list(self.session.scalars(stmt).all())

    def get_by_entity_and_key(self, entity_type: str, field_key: str) -> FieldMeta | None:
        stmt = select(FieldMeta).where(
            FieldMeta.entity_type == entity_type.upper(),
            FieldMeta.field_key == field_key,
        )
        return self.session.scalar(stmt)
