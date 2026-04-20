from collections.abc import Callable
from typing import Any

from sqlalchemy import or_, select, String, cast
from sqlalchemy.orm import Session

from app.audit.diff import diff_fields
from app.models.reference import FieldMeta
from app.utils.field_key_mapping import field_key_to_model_attr
from app.repositories.base import BaseRepository
from app.repositories.field_meta_repository import FieldMetaRepository
from app.services.audit_service import AuditService
from app.services.code_service import CodeService
from app.validators.entity_validator import normalize_value_for_meta, validate_field_value


class BaseEntityService:
    def __init__(
        self,
        session: Session,
        entity_type: str,
        model_cls: type,
        repository_factory: Callable[[Session], BaseRepository],
    ) -> None:
        self.session = session
        self.entity_type = entity_type.upper()
        self.model_cls = model_cls
        self.repo = repository_factory(session)
        self.meta_repo = FieldMetaRepository(session)
        self.code_service = CodeService(session)
        self.audit_service = AuditService(session)

    def _metas(self) -> list[FieldMeta]:
        return self.meta_repo.list_by_entity(self.entity_type)

    def _to_values(self, obj: Any) -> dict[str, str | None]:
        return {field_key_to_model_attr(meta.field_key): getattr(obj, field_key_to_model_attr(meta.field_key)) for meta in self._metas()}

    def list(self, search_text: str = "") -> list[Any]:
        stmt = select(self.model_cls)
        if search_text:
            conditions = [
                cast(getattr(self.model_cls, field_key_to_model_attr(meta.field_key)), String).ilike(f"%{search_text}%")
                for meta in self._metas()
            ]
            if conditions:
                stmt = stmt.where(or_(*conditions))
        stmt = stmt.order_by(self.model_cls.id.asc())
        return list(self.session.scalars(stmt).all())

    def get(self, obj_id: int) -> Any | None:
        return self.repo.get(obj_id)

    def _normalize_row_values(self, values: dict[str, str | None]) -> dict[str, str | None]:
        out = {**values}
        for meta in self._metas():
            key = field_key_to_model_attr(meta.field_key)
            raw = out.get(key)
            try:
                out[key] = normalize_value_for_meta(meta, raw)
            except ValueError as exc:
                raise ValueError(f"{meta.display_name}: {exc}") from exc
        return out

    def _validate_values(self, values: dict[str, str | None]) -> None:
        for meta in self._metas():
            key = field_key_to_model_attr(meta.field_key)
            value = values.get(key)
            validate_field_value(meta, value)
            ft = (meta.field_type or "text").strip().lower()
            if ft == "code":
                if not meta.code_group_id:
                    raise ValueError(f"{meta.display_name}: code group is not configured.")
                if value and not self.code_service.validate_code(meta.code_group_id, value):
                    raise ValueError(f"{meta.display_name}: invalid code '{value}'.")

    def create(self, values: dict[str, str | None]) -> Any:
        norm = self._normalize_row_values(values)
        self._validate_values(norm)
        obj = self.model_cls()
        for meta in self._metas():
            attr = field_key_to_model_attr(meta.field_key)
            setattr(obj, attr, norm.get(attr))
        self.repo.add(obj)
        after = self._to_values(obj)
        self.audit_service.log(
            entity_type=self.entity_type,
            entity_id=obj.id,
            action="CREATE",
            before_data=None,
            after_data=after,
            changed_fields=list(after.keys()),
        )
        return obj

    def update(self, obj_id: int, values: dict[str, str | None]) -> Any:
        obj = self.get(obj_id)
        if not obj:
            raise ValueError(f"{self.entity_type} id={obj_id} not found.")
        before = self._to_values(obj)
        merged = {**before, **values}
        norm_merged = self._normalize_row_values(merged)
        self._validate_values(norm_merged)
        for key in values:
            setattr(obj, key, norm_merged.get(key))
        after = self._to_values(obj)
        changed = diff_fields(before, after)
        if changed:
            self.audit_service.log(
                entity_type=self.entity_type,
                entity_id=obj.id,
                action="UPDATE",
                before_data={k: before.get(k) for k in changed},
                after_data={k: after.get(k) for k in changed},
                changed_fields=changed,
            )
        return obj

    def delete(self, obj_id: int) -> None:
        obj = self.get(obj_id)
        if not obj:
            raise ValueError(f"{self.entity_type} id={obj_id} not found.")
        before = self._to_values(obj)
        self.repo.delete(obj)
        self.audit_service.log(
            entity_type=self.entity_type,
            entity_id=obj_id,
            action="DELETE",
            before_data=before,
            after_data=None,
            changed_fields=list(before.keys()),
        )
