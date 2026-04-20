from sqlalchemy.orm import Session

from app.models.entities import C
from app.repositories.entity_repository import CRepository
from app.services.base_entity_service import BaseEntityService


class CService(BaseEntityService):
    def __init__(self, session: Session) -> None:
        super().__init__(session, "C", C, CRepository)
