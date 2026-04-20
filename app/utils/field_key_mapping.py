"""FieldMeta.field_key (A00–D19 등) ↔ SQLAlchemy 엔티티 컬럼 속성명 (a0–d19)."""

from app.core.config import ENTITY_FIELD_SLOT_COUNT


def field_key_to_model_attr(field_key: str) -> str:
    """예: A00, B19 → a0, b19."""
    fk = (field_key or "").strip().upper()
    if len(fk) < 2 or fk[0] not in "ABCD":
        raise ValueError(f"Invalid field_key: {field_key!r}")
    suf = fk[1:]
    if not suf.isdigit():
        raise ValueError(f"Invalid field_key: {field_key!r}")
    n = int(suf)
    if n < 0 or n >= ENTITY_FIELD_SLOT_COUNT:
        raise ValueError(f"Invalid field_key: {field_key!r}")
    return f"{fk[0].lower()}{n}"
