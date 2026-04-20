from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import DEFAULT_TEXT_MAX_LENGTH
from app.core.database import Base


class CodeGroup(Base):
    __tablename__ = "code_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    codes: Mapped[list["Code"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class Code(Base):
    __tablename__ = "codes"
    __table_args__ = (UniqueConstraint("group_id", "code", name="uq_group_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("code_groups.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), nullable=False)
    label: Mapped[str] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    group: Mapped[CodeGroup] = relationship(back_populates="codes")


class FieldMeta(Base):
    __tablename__ = "field_meta"
    __table_args__ = (UniqueConstraint("entity_type", "field_key", name="uq_entity_field"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(1), nullable=False, index=True)
    field_key: Mapped[str] = mapped_column(String(5), nullable=False)
    display_name: Mapped[str] = mapped_column(String(DEFAULT_TEXT_MAX_LENGTH), nullable=False)
    field_type: Mapped[str] = mapped_column(String(10), default="text", nullable=False)
    code_group_id: Mapped[int | None] = mapped_column(ForeignKey("code_groups.id"), nullable=True)
    allow_null: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_length: Mapped[int] = mapped_column(Integer, default=DEFAULT_TEXT_MAX_LENGTH, nullable=False)
    in_use: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    code_group: Mapped[CodeGroup | None] = relationship()
