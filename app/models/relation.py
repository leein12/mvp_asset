from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.entities import A, B, C

# REMOVED_ASSET_MAPPING_TAB: UI 비활성. 무결성·기존 DB 호환을 위해 모델·테이블 유지.


class Relation(Base):
    __tablename__ = "relations"
    __table_args__ = (
        UniqueConstraint("a_id", "b_id", "c_id", name="uq_relation_triplet"),
        UniqueConstraint("asset_management_no", name="uq_relation_asset_management_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_management_no: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    a_id: Mapped[int] = mapped_column(ForeignKey("a.id"), index=True, nullable=False)
    b_id: Mapped[int] = mapped_column(ForeignKey("b.id"), index=True, nullable=False)
    c_id: Mapped[int] = mapped_column(ForeignKey("c.id"), index=True, nullable=False)
    relation_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    a: Mapped[A] = relationship()
    b: Mapped[B] = relationship()
    c: Mapped[C] = relationship()
