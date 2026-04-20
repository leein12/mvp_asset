"""날짜 필드: YYYY-MM-DD 및 숫자만 입력(8자리) 정규화."""

from __future__ import annotations

import re
from datetime import date, datetime


def normalize_date_input(raw: str | None) -> str | None:
    """비어 있으면 None. 숫자 8자리면 YYYY-MM-DD. 이미 대시 포함 형식이면 정리 후 검증."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:
        y, m, d = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
        return _validate_ymd(y, m, d)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        y, m, d = (int(x) for x in s.split("-"))
        return _validate_ymd(y, m, d)
    raise ValueError(f"날짜는 YYYY-MM-DD 또는 숫자 8자리(YYYYMMDD)여야 합니다. (입력: {s[:32]})")


def _validate_ymd(y: int, m: int, d: int) -> str:
    try:
        date(y, m, d)
    except ValueError as exc:
        raise ValueError(f"유효하지 않은 날짜입니다: {y:04d}-{m:02d}-{d:02d}") from exc
    return f"{y:04d}-{m:02d}-{d:02d}"


def is_valid_date_string(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False
