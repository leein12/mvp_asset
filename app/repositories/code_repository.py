from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import Code, CodeGroup
from app.repositories.base import BaseRepository


class CodeGroupRepository(BaseRepository[CodeGroup]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CodeGroup)

    def list_all(self) -> list[CodeGroup]:  # type: ignore[override]
        stmt = select(CodeGroup).order_by(CodeGroup.id.asc())
        return list(self.session.scalars(stmt).all())

    def find_by_name(self, name: str) -> CodeGroup | None:
        stmt = select(CodeGroup).where(CodeGroup.name == name)
        return self.session.scalar(stmt)


class CodeRepository(BaseRepository[Code]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Code)

    def find_code(self, group_id: int, code: str) -> Code | None:
        stmt = select(Code).where(Code.group_id == group_id, Code.code == code, Code.is_active.is_(True))
        return self.session.scalar(stmt)

    def find_duplicate_in_group(self, group_id: int, code: str, exclude_id: int | None = None) -> Code | None:
        stmt = select(Code).where(Code.group_id == group_id, Code.code == code)
        if exclude_id is not None:
            stmt = stmt.where(Code.id != exclude_id)
        return self.session.scalar(stmt)

    def list_by_group(self, group_id: int) -> list[Code]:
        stmt = select(Code).where(Code.group_id == group_id).order_by(Code.code.asc())
        return list(self.session.scalars(stmt).all())

    def list_by_group_order_id(self, group_id: int) -> list[Code]:
        stmt = (
            select(Code)
            .where(Code.group_id == group_id, Code.is_active.is_(True))
            .order_by(Code.id.asc())
        )
        return list(self.session.scalars(stmt).all())
