from pydantic import BaseModel, Field

from app.core.config import DEFAULT_TEXT_MAX_LENGTH
from app.schemas.common import ORMModel


class EntityPayload(BaseModel):
    values: dict[str, str | None] = Field(default_factory=dict)


class EntityRead(ORMModel):
    id: int
    values: dict[str, str | None]


class FieldMetaRead(ORMModel):
    id: int
    entity_type: str
    field_key: str
    display_name: str
    field_type: str = "text"
    code_group_id: int | None
    allow_null: bool
    max_length: int = DEFAULT_TEXT_MAX_LENGTH
    in_use: bool = True
