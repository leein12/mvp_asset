from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RelationCreate(BaseModel):
    a_id: int
    b_id: int
    c_id: int
    relation_meta: dict = Field(default_factory=dict)


class RelationRead(ORMModel):
    id: int
    a_id: int
    b_id: int
    c_id: int
    relation_meta: dict | None
