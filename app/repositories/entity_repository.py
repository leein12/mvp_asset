from sqlalchemy.orm import Session

from app.models.entities import A, B, C, D
from app.repositories.base import BaseRepository


class ARepository(BaseRepository[A]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, A)


class BRepository(BaseRepository[B]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, B)


class CRepository(BaseRepository[C]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, C)


class DRepository(BaseRepository[D]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, D)
