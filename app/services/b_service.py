from sqlalchemy.orm import Session

from app.models.entities import B
from app.repositories.entity_repository import BRepository
from app.services.base_entity_service import BaseEntityService


class BService(BaseEntityService):
    def __init__(self, session: Session) -> None:
        super().__init__(session, "B", B, BRepository)
