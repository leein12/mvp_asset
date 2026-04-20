from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import A, B, C, D
from app.models.reference import Code, FieldMeta
from app.utils.field_key_mapping import field_key_to_model_attr
from app.models.relation import Relation


class IntegrityService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_invalid_codes(self) -> list[dict]:
        results: list[dict] = []
        entity_map = {"A": A, "B": B, "C": C, "D": D}
        metas = list(
            self.session.scalars(
                select(FieldMeta).where(FieldMeta.field_type == "code", FieldMeta.in_use.is_(True))
            ).all()
        )
        for meta in metas:
            model = entity_map.get(meta.entity_type)
            if not model or not meta.code_group_id:
                continue
            column = getattr(model, field_key_to_model_attr(meta.field_key))
            rows = self.session.execute(select(model.id, column).where(column.is_not(None))).all()
            for entity_id, value in rows:
                code_exists = self.session.scalar(
                    select(Code.id).where(
                        Code.group_id == meta.code_group_id,
                        Code.code == value,
                        Code.is_active.is_(True),
                    )
                )
                if not code_exists:
                    results.append(
                        {
                            "entity_type": meta.entity_type,
                            "entity_id": entity_id,
                            "field_key": meta.field_key,
                            "invalid_code": value,
                        }
                    )
        return results

    def find_orphan_relations(self) -> list[dict]:
        rows = self.session.execute(
            select(Relation).where(
                Relation.a_id.not_in(select(A.id))
                | Relation.b_id.not_in(select(B.id))
                | Relation.c_id.not_in(select(C.id))
            )
        ).scalars()
        return [
            {
                "relation_id": r.id,
                "asset_management_no": r.asset_management_no,
                "a_id": r.a_id,
                "b_id": r.b_id,
                "c_id": r.c_id,
            }
            for r in rows
        ]

    def find_duplicate_relations(self) -> list[dict]:
        duplicate_groups = self.session.execute(
            select(Relation.a_id, Relation.b_id, Relation.c_id, func.count(Relation.id).label("cnt"))
            .group_by(Relation.a_id, Relation.b_id, Relation.c_id)
            .having(func.count(Relation.id) > 1)
        ).all()
        return [{"a_id": a_id, "b_id": b_id, "c_id": c_id, "count": cnt} for a_id, b_id, c_id, cnt in duplicate_groups]
