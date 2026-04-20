from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CRUDResult(BaseModel):
    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None
