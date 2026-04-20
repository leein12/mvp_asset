from pydantic import BaseModel

from app.schemas.common import ORMModel


class CodeGroupCreate(BaseModel):
    name: str


class CodeCreate(BaseModel):
    group_id: int
    code: str
    label: str
    is_active: bool = True


class CodeRead(ORMModel):
    id: int
    group_id: int
    code: str
    label: str
    is_active: bool
