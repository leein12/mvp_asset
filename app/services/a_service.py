from sqlalchemy.orm import Session

from app.models.entities import A
from app.repositories.entity_repository import ARepository
from app.services.base_entity_service import BaseEntityService


class AService(BaseEntityService):
    def __init__(self, session: Session) -> None:
        super().__init__(session, "A", A, ARepository)
