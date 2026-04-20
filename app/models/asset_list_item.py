"""자산 리스트 전용 행 (Relation/자산 매핑과 별도 테이블)."""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import DEFAULT_TEXT_MAX_LENGTH
from app.core.database import Base
from app.models.entities import A, B, TimestampMixin


class AssetListItem(Base, TimestampMixin):
    __tablename__ = "asset_list_items"
    __table_args__ = (UniqueConstraint("asset_management_no", name="uq_asset_list_item_asset_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_management_no: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    a_id: Mapped[int] = mapped_column(ForeignKey("a.id"), nullable=False, index=True)
    b_hyup_id: Mapped[int | None] = mapped_column(ForeignKey("b.id"), nullable=True, index=True)
    b_dt_id: Mapped[int | None] = mapped_column(ForeignKey("b.id"), nullable=True, index=True)
    b_ito_id: Mapped[int | None] = mapped_column(ForeignKey("b.id"), nullable=True, index=True)
    b_ops_id: Mapped[int | None] = mapped_column(ForeignKey("b.id"), nullable=True, index=True)
    hostname: Mapped[str | None] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    server_cls: Mapped[str | None] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    port: Mapped[str | None] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    server_kind: Mapped[str | None] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)

    a_row: Mapped[A] = relationship()
    b_hyup: Mapped[B | None] = relationship(foreign_keys=[b_hyup_id])
    b_dt: Mapped[B | None] = relationship(foreign_keys=[b_dt_id])
    b_ito: Mapped[B | None] = relationship(foreign_keys=[b_ito_id])
    b_ops: Mapped[B | None] = relationship(foreign_keys=[b_ops_id])
