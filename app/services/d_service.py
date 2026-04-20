from sqlalchemy.orm import Session

from app.models.entities import D
from app.repositories.entity_repository import DRepository
from app.services.base_entity_service import BaseEntityService


class DService(BaseEntityService):
    def __init__(self, session: Session) -> None:
        super().__init__(session, "D", D, DRepository)
