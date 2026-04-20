import re

from app.models.reference import FieldMeta
from app.utils.date_input import is_valid_date_string, normalize_date_input


def normalize_value_for_meta(meta: FieldMeta, value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    ft = (meta.field_type or "text").strip().lower()
    if ft == "date":
        return normalize_date_input(s)
    return s


def validate_field_value(meta: FieldMeta, value: str | None) -> None:
    if (value is None or value == "") and not meta.allow_null:
        raise ValueError(f"{meta.display_name} is required.")
    if value is None or value == "":
        return
    ft = (meta.field_type or "text").strip().lower()
    if ft == "date":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(f"{meta.display_name}: 날짜는 YYYY-MM-DD 형식이어야 합니다.")
        if not is_valid_date_string(value):
            raise ValueError(f"{meta.display_name}: 유효하지 않은 날짜입니다.")
        if len(value) > meta.max_length:
            raise ValueError(f"{meta.display_name} exceeds max length {meta.max_length}.")
        return
    if len(value) > meta.max_length:
        raise ValueError(f"{meta.display_name} exceeds max length {meta.max_length}.")
