from sqlalchemy.orm import Session

from app.core.config import ENTITY_FIELD_SLOT_COUNT
from app.models.reference import FieldMeta
from app.repositories.field_meta_repository import FieldMetaRepository

_ALLOWED_FIELD_TYPES = frozenset({"text", "date", "code"})


class FieldMetaService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = FieldMetaRepository(session)

    def list_by_entity(self, entity_type: str, *, include_unused: bool = False) -> list[FieldMeta]:
        return self.repo.list_by_entity(entity_type, include_unused=include_unused)

    def get_meta(self, meta_id: int) -> FieldMeta | None:
        return self.repo.get(meta_id)

    def _validate_field_type(self, field_type: str, code_group_id: int | None) -> str:
        ft = (field_type or "text").strip().lower()
        if ft not in _ALLOWED_FIELD_TYPES:
            raise ValueError(f"field_type은 text, date, code 중 하나여야 합니다. (입력: {field_type})")
        if ft == "code" and not code_group_id:
            raise ValueError("type이 code일 때는 code_group_id가 필요합니다.")
        if ft != "code" and code_group_id is not None:
            pass
        return ft

    def update_meta(
        self,
        meta_id: int,
        display_name: str,
        field_type: str,
        code_group_id: int | None,
        allow_null: bool,
        max_length: int,
        in_use: bool,
    ) -> FieldMeta:
        meta = self.repo.get(meta_id)
        if not meta:
            raise ValueError("FieldMeta not found.")
        ft = self._validate_field_type(field_type, code_group_id)
        meta.display_name = display_name
        meta.field_type = ft
        meta.code_group_id = code_group_id if ft == "code" else None
        meta.allow_null = allow_null
        meta.max_length = max_length
        meta.in_use = in_use
        self.session.flush()
        return meta

    def create_meta(
        self,
        entity_type: str,
        field_key: str,
        display_name: str,
        field_type: str,
        code_group_id: int | None,
        allow_null: bool,
        max_length: int,
        in_use: bool = True,
    ) -> FieldMeta:
        et = entity_type.strip().upper()
        if et not in ("A", "B", "C", "D"):
            raise ValueError("entity_type must be A, B, C, or D.")
        fk = field_key.strip().upper()
        if not fk.startswith(et):
            raise ValueError(
                f"field_key는 {et}{0:02d}~{et}{ENTITY_FIELD_SLOT_COUNT - 1:02d} 형식(접미사 2자리)이어야 합니다."
            )
        suf = fk[len(et) :]
        if len(suf) != 2 or not suf.isdigit():
            raise ValueError(
                f"field_key는 {et}{0:02d}~{et}{ENTITY_FIELD_SLOT_COUNT - 1:02d} 형식(접미사 2자리)이어야 합니다."
            )
        slot = int(suf)
        if slot < 0 or slot >= ENTITY_FIELD_SLOT_COUNT:
            raise ValueError(
                f"field_key는 {et}{0:02d}~{et}{ENTITY_FIELD_SLOT_COUNT - 1:02d} 형식(접미사 2자리)이어야 합니다."
            )
        if self.repo.get_by_entity_and_key(et, fk):
            raise ValueError("이미 등록된 field_key입니다.")
        ft = self._validate_field_type(field_type, code_group_id)
        meta = FieldMeta(
            entity_type=et,
            field_key=fk,
            display_name=display_name.strip(),
            field_type=ft,
            code_group_id=code_group_id if ft == "code" else None,
            allow_null=allow_null,
            max_length=max_length,
            in_use=in_use,
        )
        self.repo.add(meta)
        return meta

    def delete_metas(self, entity_type: str, meta_ids: list[int]) -> None:
        et = entity_type.strip().upper()
        for mid in meta_ids:
            meta = self.repo.get(mid)
            if not meta or meta.entity_type != et:
                raise ValueError(f"삭제할 항목 id={mid}을(를) 찾을 수 없거나 Entity가 다릅니다.")
            self.repo.delete(meta)
        self.session.flush()
