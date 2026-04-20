from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import DEFAULT_TEXT_MAX_LENGTH
from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class A(Base, TimestampMixin):
    __tablename__ = "a"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    a0: Mapped[str | None] = mapped_column("A0", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a1: Mapped[str | None] = mapped_column("A1", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a2: Mapped[str | None] = mapped_column("A2", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a3: Mapped[str | None] = mapped_column("A3", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a4: Mapped[str | None] = mapped_column("A4", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a5: Mapped[str | None] = mapped_column("A5", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a6: Mapped[str | None] = mapped_column("A6", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a7: Mapped[str | None] = mapped_column("A7", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a8: Mapped[str | None] = mapped_column("A8", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a9: Mapped[str | None] = mapped_column("A9", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a10: Mapped[str | None] = mapped_column("A10", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a11: Mapped[str | None] = mapped_column("A11", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a12: Mapped[str | None] = mapped_column("A12", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a13: Mapped[str | None] = mapped_column("A13", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a14: Mapped[str | None] = mapped_column("A14", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a15: Mapped[str | None] = mapped_column("A15", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a16: Mapped[str | None] = mapped_column("A16", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a17: Mapped[str | None] = mapped_column("A17", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a18: Mapped[str | None] = mapped_column("A18", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    a19: Mapped[str | None] = mapped_column("A19", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)


class B(Base, TimestampMixin):
    __tablename__ = "b"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    b0: Mapped[str | None] = mapped_column("B0", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b1: Mapped[str | None] = mapped_column("B1", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b2: Mapped[str | None] = mapped_column("B2", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b3: Mapped[str | None] = mapped_column("B3", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b4: Mapped[str | None] = mapped_column("B4", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b5: Mapped[str | None] = mapped_column("B5", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b6: Mapped[str | None] = mapped_column("B6", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b7: Mapped[str | None] = mapped_column("B7", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b8: Mapped[str | None] = mapped_column("B8", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b9: Mapped[str | None] = mapped_column("B9", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b10: Mapped[str | None] = mapped_column("B10", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b11: Mapped[str | None] = mapped_column("B11", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b12: Mapped[str | None] = mapped_column("B12", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b13: Mapped[str | None] = mapped_column("B13", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b14: Mapped[str | None] = mapped_column("B14", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b15: Mapped[str | None] = mapped_column("B15", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b16: Mapped[str | None] = mapped_column("B16", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b17: Mapped[str | None] = mapped_column("B17", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b18: Mapped[str | None] = mapped_column("B18", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    b19: Mapped[str | None] = mapped_column("B19", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)


class C(Base, TimestampMixin):
    __tablename__ = "c"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    c0: Mapped[str | None] = mapped_column("C0", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c1: Mapped[str | None] = mapped_column("C1", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c2: Mapped[str | None] = mapped_column("C2", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c3: Mapped[str | None] = mapped_column("C3", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c4: Mapped[str | None] = mapped_column("C4", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c5: Mapped[str | None] = mapped_column("C5", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c6: Mapped[str | None] = mapped_column("C6", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c7: Mapped[str | None] = mapped_column("C7", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c8: Mapped[str | None] = mapped_column("C8", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c9: Mapped[str | None] = mapped_column("C9", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c10: Mapped[str | None] = mapped_column("C10", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c11: Mapped[str | None] = mapped_column("C11", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c12: Mapped[str | None] = mapped_column("C12", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c13: Mapped[str | None] = mapped_column("C13", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c14: Mapped[str | None] = mapped_column("C14", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c15: Mapped[str | None] = mapped_column("C15", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c16: Mapped[str | None] = mapped_column("C16", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c17: Mapped[str | None] = mapped_column("C17", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c18: Mapped[str | None] = mapped_column("C18", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    c19: Mapped[str | None] = mapped_column("C19", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)


class D(Base, TimestampMixin):
    __tablename__ = "d"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    d0: Mapped[str | None] = mapped_column("D0", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d1: Mapped[str | None] = mapped_column("D1", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d2: Mapped[str | None] = mapped_column("D2", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d3: Mapped[str | None] = mapped_column("D3", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d4: Mapped[str | None] = mapped_column("D4", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d5: Mapped[str | None] = mapped_column("D5", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d6: Mapped[str | None] = mapped_column("D6", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d7: Mapped[str | None] = mapped_column("D7", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d8: Mapped[str | None] = mapped_column("D8", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d9: Mapped[str | None] = mapped_column("D9", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d10: Mapped[str | None] = mapped_column("D10", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d11: Mapped[str | None] = mapped_column("D11", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d12: Mapped[str | None] = mapped_column("D12", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d13: Mapped[str | None] = mapped_column("D13", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d14: Mapped[str | None] = mapped_column("D14", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d15: Mapped[str | None] = mapped_column("D15", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d16: Mapped[str | None] = mapped_column("D16", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d17: Mapped[str | None] = mapped_column("D17", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d18: Mapped[str | None] = mapped_column("D18", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
    d19: Mapped[str | None] = mapped_column("D19", String(DEFAULT_TEXT_MAX_LENGTH), nullable=True)
