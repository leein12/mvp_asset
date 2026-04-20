"""자산 리스트: 전용 테이블(asset_list_items). Relation/자산 매핑과 DB·조회 경로를 분리한다."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.asset_list_item import AssetListItem
from app.models.entities import A, B, C
from app.services.mapping_field_meta_keys import ROLE_SPECS, mapping_field_keys

ASSET_LIST_COLUMNS: tuple[tuple[str, str], ...] = (
    ("asset_management_no", "자산관리번호"),
    ("map_system_name", "시스템명"),
    ("map_hyup", "현업"),
    ("map_dt", "DT팀"),
    ("map_ito", "통합ITO"),
    ("map_ops", "운영자"),
    ("map_hostname", "Hostname"),
    ("map_server_cls", "서버분류"),
    ("map_ip", "IP"),
    ("map_port", "Port"),
    ("map_server_kind", "서버 구분"),
)


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _c_attr_str(c: C, attr: str | None) -> str:
    if not attr:
        return ""
    v = getattr(c, attr, None)
    return str(v).strip() if v is not None else ""


class AssetListService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def column_specs(self) -> list[dict[str, str]]:
        return [{"key": key, "label": label} for key, label in ASSET_LIST_COLUMNS]

    def build_page_context(self) -> dict[str, Any]:
        """datalist용 자산 리스트 전용 필드 추천. Hostname 후보는 자산 관리(C) API로 조회한다."""
        return {
            "mapping_keys": mapping_field_keys(self.session),
            "c_suggest_server_cls": self._distinct_item_field("server_cls"),
            "c_suggest_ip": self._distinct_item_field("ip"),
            "c_suggest_port": self._distinct_item_field("port"),
            "c_suggest_server_kind": self._distinct_item_field("server_kind"),
        }

    def _distinct_item_field(self, attr: str) -> list[str]:
        col = getattr(AssetListItem, attr, None)
        if col is None:
            return []
        seen: set[str] = set()
        out: list[str] = []
        for v in self.session.scalars(select(col).where(col.isnot(None)).distinct()).all():
            if v is None:
                continue
            s = str(v).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out

    def suggest_systems(self, q: str, limit: int = 25) -> list[dict[str, Any]]:
        """시스템관리(A) 시스템명 컬럼 LIKE 검색 후 id·표시 라벨."""
        q = (q or "").strip()
        if not q:
            return []
        k = mapping_field_keys(self.session)
        a_attr = k.get("a_system")
        if not a_attr:
            return []
        col = getattr(A, a_attr, None)
        if col is None:
            return []
        pat = f"%{_escape_like(q)}%"
        rows = list(
            self.session.scalars(select(A).where(col.like(pat, escape="\\")).order_by(A.id.asc()).limit(limit)).all()
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            lab = getattr(r, a_attr, None)
            label = str(lab).strip() if lab is not None else f"#{r.id}"
            out.append({"id": r.id, "label": label})
        return out

    def suggest_b_by_role(self, role_key: str, q: str, limit: int = 25) -> list[dict[str, Any]]:
        """담당자(B) 성명 LIKE. 현업(hyup)은 역할 필드가 정확히 '현업'인 행만(담당자 관리 기준)."""
        rk = (role_key or "").strip().lower()
        q = (q or "").strip()
        if not q or rk not in {"hyup", "dt", "ito", "ops"}:
            return []
        k = mapping_field_keys(self.session)
        role_attr = k.get("b_role")
        name_attr = k.get("b_name")
        if not role_attr or not name_attr:
            return []
        name_col = getattr(B, name_attr, None)
        role_col = getattr(B, role_attr, None)
        if name_col is None or role_col is None:
            return []
        pat = f"%{_escape_like(q)}%"

        if rk == "hyup":
            stmt = (
                select(B)
                .where(
                    and_(
                        role_col.isnot(None),
                        func.trim(role_col) == "현업",
                        name_col.isnot(None),
                        name_col.like(pat, escape="\\"),
                    )
                )
                .order_by(B.id.asc())
                .limit(limit)
            )
            out: list[dict[str, Any]] = []
            for b in self.session.scalars(stmt).all():
                lab = getattr(b, name_attr, None)
                label = str(lab).strip() if lab is not None else f"#{b.id}"
                out.append({"id": b.id, "label": label})
            return out

        hints: tuple[str, ...] | None = None
        for role_spec, hs in ROLE_SPECS:
            if role_spec == rk:
                hints = hs
                break
        if hints is None:
            return []
        candidates = list(
            self.session.scalars(
                select(B).where(name_col.like(pat, escape="\\")).order_by(B.id.asc()).limit(max(limit * 8, 40))
            ).all()
        )
        out = []
        for b in candidates:
            rv = str(getattr(b, role_attr, None) or "").strip()
            if not rv:
                continue
            if not any(h in rv or rv == h for h in hints):
                continue
            lab = getattr(b, name_attr, None)
            label = str(lab).strip() if lab is not None else f"#{b.id}"
            out.append({"id": b.id, "label": label})
            if len(out) >= limit:
                break
        return out

    def suggest_hostnames(self, q: str, limit: int = 25) -> list[dict[str, Any]]:
        """자산 관리(C) Hostname LIKE. 후보에 동일 C행의 서버분류·IP·Port·서버 구분 포함(선택 시 UI 채움)."""
        q = (q or "").strip()
        if not q:
            return []
        k = mapping_field_keys(self.session)
        host_attr = k.get("c_hostname")
        if not host_attr:
            return []
        col = getattr(C, host_attr, None)
        if col is None:
            return []
        pat = f"%{_escape_like(q)}%"
        rows = list(
            self.session.scalars(
                select(C).where(col.isnot(None), col.like(pat, escape="\\")).order_by(C.id.asc()).limit(max(limit * 4, 40))
            ).all()
        )
        out: list[dict[str, Any]] = []
        seen_labels: set[str] = set()
        for c in rows:
            hv = getattr(c, host_attr, None)
            label = str(hv).strip() if hv is not None else ""
            if not label or label in seen_labels:
                continue
            seen_labels.add(label)
            out.append(
                {
                    "id": c.id,
                    "label": label,
                    "server_cls": _c_attr_str(c, k.get("c_server_cls")),
                    "ip": _c_attr_str(c, k.get("c_ip")),
                    "port": _c_attr_str(c, k.get("c_port")),
                    "server_kind": _c_attr_str(c, k.get("c_server_kind")),
                }
            )
            if len(out) >= limit:
                break
        return out

    def _next_asset_management_no(self) -> str:
        rows = list(self.session.scalars(select(AssetListItem.asset_management_no)).all())
        mx = 0
        for raw in rows:
            s = str(raw or "").strip().upper()
            if s.startswith("CA") and len(s) > 2 and s[2:].isdigit():
                mx = max(mx, int(s[2:]))
            elif s.isdigit():
                mx = max(mx, int(s))
        nxt = mx + 1
        if nxt > 99_999:
            raise ValueError("자산관리번호(CA#####)는 CA99999를 넘을 수 없습니다.")
        return f"CA{nxt:05d}"

    def _b_name(self, bobj: B | None, name_attr: str | None) -> Any:
        if bobj is None or not name_attr:
            return None
        return getattr(bobj, name_attr, None)

    def _row_to_display(self, item: AssetListItem) -> dict[str, Any]:
        k = mapping_field_keys(self.session)
        b_name = k.get("b_name")
        a = item.a_row
        a_attr = k.get("a_system")
        sys_name = getattr(a, a_attr, None) if a is not None and a_attr else None
        return {
            "id": item.id,
            "a_id": item.a_id,
            "b_hyup_id": item.b_hyup_id,
            "b_dt_id": item.b_dt_id,
            "b_ito_id": item.b_ito_id,
            "b_ops_id": item.b_ops_id,
            "asset_management_no": item.asset_management_no,
            "map_system_name": sys_name,
            "map_hyup": self._b_name(item.b_hyup, b_name),
            "map_dt": self._b_name(item.b_dt, b_name),
            "map_ito": self._b_name(item.b_ito, b_name),
            "map_ops": self._b_name(item.b_ops, b_name),
            "map_hostname": item.hostname,
            "map_server_cls": item.server_cls,
            "map_ip": item.ip,
            "map_port": item.port,
            "map_server_kind": item.server_kind,
        }

    def _alist_search_where(self, q: str):
        q = (q or "").strip()
        if not q:
            return None
        pat = f"%{_escape_like(q)}%"
        k = mapping_field_keys(self.session)
        a_attr = k.get("a_system") or "a0"
        b_name_attr = k.get("b_name") or "b0"
        a_col = getattr(A, a_attr, None)
        bn_col = getattr(B, b_name_attr, None)
        parts: list[Any] = [
            AssetListItem.asset_management_no.like(pat, escape="\\"),
            AssetListItem.hostname.like(pat, escape="\\"),
            AssetListItem.server_cls.like(pat, escape="\\"),
            AssetListItem.ip.like(pat, escape="\\"),
            AssetListItem.port.like(pat, escape="\\"),
            AssetListItem.server_kind.like(pat, escape="\\"),
        ]
        if a_col is not None:
            parts.append(exists(select(1).where(A.id == AssetListItem.a_id, a_col.like(pat, escape="\\"))))
        if bn_col is not None:
            for fk in ("b_hyup_id", "b_dt_id", "b_ito_id", "b_ops_id"):
                bid = getattr(AssetListItem, fk)
                parts.append(exists(select(1).where(and_(B.id == bid, bn_col.like(pat, escape="\\")))))
        return or_(*parts)

    def list_page_rows(self, page: int, per_page: int, q: str = "") -> tuple[list[dict[str, Any]], int, int]:
        filt = self._alist_search_where(q)
        cnt_stmt = select(func.count(AssetListItem.id))
        list_stmt = select(AssetListItem).order_by(AssetListItem.id.asc())
        if filt is not None:
            cnt_stmt = cnt_stmt.where(filt)
            list_stmt = list_stmt.where(filt)
        total = int(self.session.scalar(cnt_stmt) or 0)
        total_pages = max(1, (total + per_page - 1) // per_page) if total else 1
        page = min(max(1, page), total_pages)
        offset = (page - 1) * per_page
        items = list(self.session.scalars(list_stmt.offset(offset).limit(per_page)).all())
        rows_out = [self._row_to_display(it) for it in items]
        return rows_out, total, page

    def _parse_int(self, v: Any) -> int | None:
        if v is None:
            return None
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            if math.isnan(v):
                return None
            if v == int(v):
                return int(v)
            return None
        s = str(v).strip()
        if not s:
            return None
        if "." in s:
            try:
                f = float(s)
                if not math.isnan(f) and f == int(f):
                    return int(f)
            except ValueError:
                pass
        return int(s) if s.isdigit() else None

    def iter_all_items_display(self) -> list[dict[str, Any]]:
        items = list(self.session.scalars(select(AssetListItem).order_by(AssetListItem.id.asc())).all())
        return [self._row_to_display(it) for it in items]

    @staticmethod
    def _excel_str(raw: dict[str, Any], label: str) -> str:
        v = raw.get(label)
        if v is None:
            return ""
        if isinstance(v, float) and math.isnan(v):
            return ""
        return str(v).strip()

    def _resolve_a_id_from_system_name(self, text: str) -> int | None:
        text = (text or "").strip()
        if not text:
            return None
        k = mapping_field_keys(self.session)
        a_attr = k.get("a_system") or "a0"
        col = getattr(A, a_attr, None)
        if col is None:
            return None
        aid = self.session.scalar(select(A.id).where(func.trim(col) == text).order_by(A.id.asc()).limit(1))
        if aid is not None:
            return int(aid)
        pat = f"%{_escape_like(text)}%"
        aid2 = self.session.scalar(select(A.id).where(col.like(pat, escape="\\")).order_by(A.id.asc()).limit(1))
        return int(aid2) if aid2 is not None else None

    def _resolve_b_hyup_id_from_name(self, text: str) -> int | None:
        text = (text or "").strip()
        if not text:
            return None
        k = mapping_field_keys(self.session)
        role_attr = k.get("b_role")
        name_attr = k.get("b_name")
        if not role_attr or not name_attr:
            return None
        name_col = getattr(B, name_attr, None)
        role_col = getattr(B, role_attr, None)
        if name_col is None or role_col is None:
            return None
        bid = self.session.scalar(
            select(B.id)
            .where(func.trim(name_col) == text, func.trim(role_col) == "현업")
            .order_by(B.id.asc())
            .limit(1)
        )
        return int(bid) if bid is not None else None

    def _resolve_b_id_for_role_display(self, role_key: str, text: str) -> int | None:
        text = (text or "").strip()
        if not text:
            return None
        k = mapping_field_keys(self.session)
        role_attr = k.get("b_role")
        name_attr = k.get("b_name")
        if not role_attr or not name_attr:
            return None
        name_col = getattr(B, name_attr, None)
        role_col = getattr(B, role_attr, None)
        if name_col is None or role_col is None:
            return None
        hints: tuple[str, ...] | None = None
        for rk, hs in ROLE_SPECS:
            if rk == role_key:
                hints = hs
                break
        if not hints:
            return None
        bid = self.session.scalar(select(B.id).where(func.trim(name_col) == text).order_by(B.id.asc()).limit(1))
        if bid is not None:
            b = self.session.get(B, int(bid))
            if b:
                rv = str(getattr(b, role_attr, None) or "").strip()
                if any(h in rv or rv == h for h in hints):
                    return int(bid)
        pat = f"%{_escape_like(text)}%"
        for b in self.session.scalars(select(B).where(name_col.like(pat, escape="\\")).order_by(B.id.asc())).all():
            rv = str(getattr(b, role_attr, None) or "").strip()
            if not rv:
                continue
            if any(h in rv or rv == h for h in hints):
                return int(b.id)
        return None

    def parse_import_row(self, raw: dict[str, Any]) -> tuple[int | None, dict[str, Any]]:
        """엑셀 한 행(dict)을 (기존 id 또는 None, create/update 공통 form dict)으로 변환."""
        raw = {str(k).strip(): v for k, v in raw.items()}
        item_id = self._parse_int(raw.get("id"))

        a_id = self._parse_int(raw.get("a_id"))
        if not a_id:
            a_id = self._resolve_a_id_from_system_name(self._excel_str(raw, "시스템명"))
        if not a_id:
            raise ValueError("시스템명 또는 a_id로 시스템관리(A) 행을 찾을 수 없습니다.")

        b_hyup_id = self._parse_int(raw.get("b_hyup_id"))
        if not b_hyup_id:
            b_hyup_id = self._resolve_b_hyup_id_from_name(self._excel_str(raw, "현업"))

        b_dt_id = self._parse_int(raw.get("b_dt_id"))
        if not b_dt_id:
            b_dt_id = self._resolve_b_id_for_role_display("dt", self._excel_str(raw, "DT팀"))

        b_ito_id = self._parse_int(raw.get("b_ito_id"))
        if not b_ito_id:
            b_ito_id = self._resolve_b_id_for_role_display("ito", self._excel_str(raw, "통합ITO"))

        b_ops_id = self._parse_int(raw.get("b_ops_id"))
        if not b_ops_id:
            b_ops_id = self._resolve_b_id_for_role_display("ops", self._excel_str(raw, "운영자"))

        def opt(label: str) -> str | None:
            s = self._excel_str(raw, label)
            return s or None

        form: dict[str, Any] = {
            "a_id": a_id,
            "b_hyup_id": b_hyup_id,
            "b_dt_id": b_dt_id,
            "b_ito_id": b_ito_id,
            "b_ops_id": b_ops_id,
            "hostname": opt("Hostname"),
            "server_cls": opt("서버분류"),
            "ip": opt("IP"),
            "port": opt("Port"),
            "server_kind": opt("서버 구분"),
        }
        return item_id, form

    def _validate_b_hyup_id(self, b_id: int | None) -> None:
        """현업: 담당자(B) 중 역할 필드가 정확히 '현업'인 행만 허용."""
        if not b_id:
            return
        b = self.session.get(B, b_id)
        if not b:
            raise ValueError("현업: 담당자 관리에 등록된 성명을 선택하세요.")
        k = mapping_field_keys(self.session)
        role_attr = k.get("b_role")
        if not role_attr:
            raise ValueError("현업: FieldMeta에 담당자 역할 필드를 설정하세요.")
        rv = str(getattr(b, role_attr, None) or "").strip()
        if rv != "현업":
            raise ValueError("현업: 담당자 관리에서 역할이 '현업'인 성명만 선택할 수 있습니다.")

    def create_from_form(self, d: dict[str, Any]) -> AssetListItem:
        a_id = self._parse_int(d.get("a_id"))
        if not a_id or not self.session.get(A, a_id):
            raise ValueError("시스템명: 시스템관리에 등록된 시스템을 검색 후 선택하세요.")
        b_hyup_id = self._parse_int(d.get("b_hyup_id"))
        self._validate_b_hyup_id(b_hyup_id)
        item = AssetListItem(
            asset_management_no=self._next_asset_management_no(),
            a_id=a_id,
            b_hyup_id=b_hyup_id,
            b_dt_id=self._parse_int(d.get("b_dt_id")),
            b_ito_id=self._parse_int(d.get("b_ito_id")),
            b_ops_id=self._parse_int(d.get("b_ops_id")),
            hostname=(str(d.get("hostname") or "").strip() or None),
            server_cls=(str(d.get("server_cls") or "").strip() or None),
            ip=(str(d.get("ip") or "").strip() or None),
            port=(str(d.get("port") or "").strip() or None),
            server_kind=(str(d.get("server_kind") or "").strip() or None),
        )
        self.session.add(item)
        self.session.flush()
        return item

    def update_from_form(self, item_id: int, d: dict[str, Any]) -> AssetListItem:
        item = self.session.get(AssetListItem, item_id)
        if not item:
            raise ValueError("자산 리스트 행을 찾을 수 없습니다.")
        a_id = self._parse_int(d.get("a_id"))
        if not a_id or not self.session.get(A, a_id):
            raise ValueError("시스템명: 시스템관리에 등록된 시스템을 검색 후 선택하세요.")
        item.a_id = a_id
        b_hyup_id = self._parse_int(d.get("b_hyup_id"))
        self._validate_b_hyup_id(b_hyup_id)
        item.b_hyup_id = b_hyup_id
        item.b_dt_id = self._parse_int(d.get("b_dt_id"))
        item.b_ito_id = self._parse_int(d.get("b_ito_id"))
        item.b_ops_id = self._parse_int(d.get("b_ops_id"))
        item.hostname = str(d.get("hostname") or "").strip() or None
        item.server_cls = str(d.get("server_cls") or "").strip() or None
        item.ip = str(d.get("ip") or "").strip() or None
        item.port = str(d.get("port") or "").strip() or None
        item.server_kind = str(d.get("server_kind") or "").strip() or None
        return item

    def delete_ids(self, ids: list[int]) -> None:
        for i in ids:
            obj = self.session.get(AssetListItem, i)
            if obj:
                self.session.delete(obj)
