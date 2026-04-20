from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.relation import Relation
from app.repositories.base import BaseRepository


class RelationRepository(BaseRepository[Relation]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Relation)

    def find_by_triplet(
        self,
        a_id: int,
        b_id: int,
        c_id: int,
        *,
        exclude_relation_id: int | None = None,
    ) -> Relation | None:
        stmt = select(Relation).where(Relation.a_id == a_id, Relation.b_id == b_id, Relation.c_id == c_id)
        if exclude_relation_id is not None:
            stmt = stmt.where(Relation.id != exclude_relation_id)
        return self.session.scalar(stmt)
