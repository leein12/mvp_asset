from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, session: Session, model_cls: type[ModelType]) -> None:
        self.session = session
        self.model_cls = model_cls

    def get(self, obj_id: int) -> ModelType | None:
        return self.session.get(self.model_cls, obj_id)

    def list_all(self) -> list[ModelType]:
        return list(self.session.scalars(select(self.model_cls)).all())

    def add(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.flush()
        return obj

    def delete(self, obj: ModelType) -> None:
        self.session.delete(obj)
