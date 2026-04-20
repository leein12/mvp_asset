from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import A, B, C
from app.models.relation import Relation
from app.repositories.relation_repository import RelationRepository
from app.services.audit_service import AuditService


class RelationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = RelationRepository(session)
        self.audit = AuditService(session)

    def list_relations(self) -> list[Relation]:
        stmt = select(Relation).order_by(Relation.id.asc())
        return list(self.session.scalars(stmt).all())

    def _next_asset_management_no(self) -> str:
        rows = list(self.session.scalars(select(Relation.asset_management_no)).all())
        mx = 0
        for raw in rows:
            s = str(raw or "").strip().upper()
            if s.startswith("CA") and len(s) > 2 and s[2:].isdigit():
                mx = max(mx, int(s[2:]))
            elif s.isdigit():
                mx = max(mx, int(s))
        nxt = mx + 1
        if nxt > 99_999:
            raise ValueError("자산관리번호(CA#####)는 CA99999를 넘을 수 없습니다.")
        return f"CA{nxt:05d}"

    def create(self, a_id: int, b_id: int, c_id: int, relation_meta: dict | None = None) -> Relation:
        if not self.session.get(A, a_id):
            raise ValueError(f"A {a_id} does not exist.")
        if not self.session.get(B, b_id):
            raise ValueError(f"B {b_id} does not exist.")
        if not self.session.get(C, c_id):
            raise ValueError(f"C {c_id} does not exist.")
        if self.repo.find_by_triplet(a_id, b_id, c_id):
            raise ValueError("Duplicate relation (A-B-C) is not allowed.")
        asset_no = self._next_asset_management_no()
        relation = Relation(
            asset_management_no=asset_no,
            a_id=a_id,
            b_id=b_id,
            c_id=c_id,
            relation_meta=relation_meta or {},
        )
        self.repo.add(relation)
        self.audit.log(
            entity_type="RELATION",
            entity_id=relation.id,
            action="CREATE",
            before_data=None,
            after_data={
                "asset_management_no": asset_no,
                "a_id": a_id,
                "b_id": b_id,
                "c_id": c_id,
                "relation_meta": relation.relation_meta,
            },
            changed_fields=["asset_management_no", "a_id", "b_id", "c_id", "relation_meta"],
        )
        return relation

    def update(
        self,
        relation_id: int,
        a_id: int,
        b_id: int,
        c_id: int,
        relation_meta: dict | None = None,
    ) -> Relation:
        relation = self.repo.get(relation_id)
        if not relation:
            raise ValueError("Relation not found.")
        if not self.session.get(A, a_id):
            raise ValueError(f"A {a_id} does not exist.")
        if not self.session.get(B, b_id):
            raise ValueError(f"B {b_id} does not exist.")
        if not self.session.get(C, c_id):
            raise ValueError(f"C {c_id} does not exist.")
        dup = self.repo.find_by_triplet(a_id, b_id, c_id, exclude_relation_id=relation_id)
        if dup:
            raise ValueError("Duplicate relation (A-B-C) is not allowed.")
        before = {
            "asset_management_no": relation.asset_management_no,
            "a_id": relation.a_id,
            "b_id": relation.b_id,
            "c_id": relation.c_id,
            "relation_meta": relation.relation_meta,
        }
        relation.a_id = a_id
        relation.b_id = b_id
        relation.c_id = c_id
        if relation_meta is not None:
            relation.relation_meta = relation_meta
        self.audit.log(
            entity_type="RELATION",
            entity_id=relation_id,
            action="UPDATE",
            before_data=before,
            after_data={
                "asset_management_no": relation.asset_management_no,
                "a_id": relation.a_id,
                "b_id": relation.b_id,
                "c_id": relation.c_id,
                "relation_meta": relation.relation_meta,
            },
            changed_fields=["a_id", "b_id", "c_id", "relation_meta"],
        )
        return relation

    def delete(self, relation_id: int) -> None:
        relation = self.repo.get(relation_id)
        if not relation:
            raise ValueError("Relation not found.")
        before = {
            "asset_management_no": relation.asset_management_no,
            "a_id": relation.a_id,
            "b_id": relation.b_id,
            "c_id": relation.c_id,
            "relation_meta": relation.relation_meta,
        }
        self.repo.delete(relation)
        self.audit.log(
            entity_type="RELATION",
            entity_id=relation_id,
            action="DELETE",
            before_data=before,
            after_data=None,
            changed_fields=["asset_management_no", "a_id", "b_id", "c_id", "relation_meta"],
        )
