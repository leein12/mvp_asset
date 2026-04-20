"""자산 매핑 UI: FieldMeta 기반 필드 해석 및 A/B/C·Relation 생성."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import A, B, C
from app.services.a_service import AService
from app.services.b_service import BService
from app.services.c_service import CService
from app.services.mapping_field_meta_keys import ROLE_SPECS as _MAPPING_ROLE_SPECS
from app.services.mapping_field_meta_keys import mapping_field_keys
from app.services.relation_service import RelationService

# --- REMOVED_ASSET_MAPPING_TAB: UI 제거됨. 리팩터링 시 이 파일·relations.html·Relation 일괄 정리 ---
# 자산 매핑 표 헤더(자산 리스트 서비스와 무관)
MAPPING_TABLE_COLUMN_SPECS: list[dict[str, str]] = [
    {"key": "asset_management_no", "label": "자산관리번호"},
    {"key": "map_system_name", "label": "시스템명"},
    {"key": "map_hyup", "label": "현업"},
    {"key": "map_dt", "label": "DT팀"},
    {"key": "map_ito", "label": "통합ITO"},
    {"key": "map_ops", "label": "운영자"},
    {"key": "map_hostname", "label": "Hostname"},
    {"key": "map_server_cls", "label": "서버분류"},
    {"key": "map_ip", "label": "IP"},
    {"key": "map_port", "label": "Port"},
    {"key": "map_server_kind", "label": "서버 구분"},
]


def _row_label(obj: Any, name_attr: str | None) -> str:
    if name_attr:
        v = getattr(obj, name_attr, None)
        if v is not None and str(v).strip():
            return f"{v} (#{obj.id})"
    return f"#{obj.id}"


class AssetMappingService:
    """자산 매핑 화면용 옵션 수집 및 매핑 저장 (탭 비활성, 레거시 유지)."""

    ROLE_SPECS = _MAPPING_ROLE_SPECS

    def __init__(self, session: Session) -> None:
        self.session = session
        self.a_svc = AService(session)
        self.b_svc = BService(session)
        self.c_svc = CService(session)
        self.rel_svc = RelationService(session)

    def get_mapping_field_keys(self) -> dict[str, str | None]:
        """자산 매핑·자산 리스트에서 사용하는 FieldMeta 기준 속성명."""
        return dict(self._keys())

    def _keys(self) -> dict[str, str | None]:
        return mapping_field_keys(self.session)

    def build_page_context(self) -> dict[str, Any]:
        k = self._keys()
        a_rows = self.a_svc.list()
        c_rows = self.c_svc.list()
        a_opts = [{"id": r.id, "label": _row_label(r, k["a_system"])} for r in a_rows]
        c_opts = [{"id": r.id, "label": self._c_row_label(r, k)} for r in c_rows]
        host_attr = k.get("c_hostname")
        c_hostname_options: list[dict[str, Any]] = []
        for r in c_rows:
            if host_attr:
                hv = getattr(r, host_attr, None)
                lab = str(hv).strip() if hv is not None and str(hv).strip() else f"#{r.id}"
            else:
                lab = f"#{r.id}"
            c_hostname_options.append({"id": r.id, "label": lab})

        role_opts: dict[str, list[dict[str, Any]]] = {}
        role_key, name_key = k["b_role"], k["b_name"]
        if role_key and name_key:
            for key, hints in self.ROLE_SPECS:
                opts: list[dict[str, Any]] = []
                for b in self.b_svc.list():
                    rv = str(getattr(b, role_key, None) or "").strip()
                    if not rv:
                        continue
                    if not any(h in rv or rv == h for h in hints):
                        continue
                    opts.append({"id": b.id, "label": _row_label(b, name_key)})
                role_opts[key] = opts
        else:
            for key, _hints in self.ROLE_SPECS:
                role_opts[key] = []

        return {
            "mapping_keys": k,
            "a_options": a_opts,
            "c_options": c_opts,
            "c_hostname_options": c_hostname_options,
            "b_role_options": role_opts,
            "c_suggest_server_cls": self._unique_c_field_values(k.get("c_server_cls")),
            "c_suggest_hostname": self._unique_c_field_values(k.get("c_hostname")),
            "c_suggest_ip": self._unique_c_field_values(k.get("c_ip")),
            "c_suggest_port": self._unique_c_field_values(k.get("c_port")),
            "c_suggest_server_kind": self._unique_c_field_values(k.get("c_server_kind")),
        }

    def _unique_c_field_values(self, attr: str | None) -> list[str]:
        if not attr:
            return []
        seen: set[str] = set()
        out: list[str] = []
        for r in self.c_svc.list():
            v = getattr(r, attr, None)
            if v is None:
                continue
            s = str(v).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out

    def rows_for_mapping_template(self, relations: list[Any]) -> list[dict[str, Any]]:
        """relations 화면: 연결된 C 행의 자산 필드 기본값."""
        k = self._keys()
        if not relations:
            return []
        c_ids = [int(r.c_id) for r in relations if getattr(r, "c_id", None)]
        cs: dict[int, C] = {}
        if c_ids:
            for c in self.session.scalars(select(C).where(C.id.in_(set(c_ids)))).all():
                cs[int(c.id)] = c

        def _c_cell(cobj: C | None, attr_key: str) -> str:
            ak = k.get(attr_key)
            if not cobj or not ak:
                return ""
            v = getattr(cobj, ak, None)
            return str(v).strip() if v is not None else ""

        out: list[dict[str, Any]] = []
        for rel in relations:
            c = cs.get(int(rel.c_id)) if getattr(rel, "c_id", None) else None
            out.append(
                {
                    "relation": rel,
                    "c_server_cls": _c_cell(c, "c_server_cls"),
                    "c_hostname": _c_cell(c, "c_hostname"),
                    "c_ip": _c_cell(c, "c_ip"),
                    "c_port": _c_cell(c, "c_port"),
                    "c_server_kind": _c_cell(c, "c_server_kind"),
                }
            )
        return out

    def display_rows_for_mapping_grid(self, relations: list[Any]) -> list[dict[str, Any]]:
        """현재 페이지 Relation 목록에 대해 자산 매핑 표와 동일한 열 dict를 만든다 (자산 리스트와 무관)."""
        if not relations:
            return []
        k = self._keys()
        a_attr = k.get("a_system")
        b_name = k.get("b_name")
        c_host = k.get("c_hostname")
        c_cls = k.get("c_server_cls")
        c_ip = k.get("c_ip")
        c_port = k.get("c_port")
        c_kind = k.get("c_server_kind")

        extra_b_ids: set[int] = set()
        for rel in relations:
            mp = (rel.relation_meta or {}).get("mapping") or {}
            for key in ("b_dt", "b_ito", "b_ops"):
                v = mp.get(key)
                if isinstance(v, int):
                    extra_b_ids.add(v)
                elif isinstance(v, str) and str(v).strip().isdigit():
                    extra_b_ids.add(int(str(v).strip()))
        b_extra: dict[int, B] = {}
        if extra_b_ids:
            for bb in self.session.scalars(select(B).where(B.id.in_(extra_b_ids))).all():
                b_extra[int(bb.id)] = bb

        def _b_name(bobj: B | None) -> Any:
            if bobj is None or not b_name:
                return None
            return getattr(bobj, b_name, None)

        rows_out: list[dict[str, Any]] = []
        for rel in relations:
            a = self.session.get(A, rel.a_id) if rel.a_id else None
            b = self.session.get(B, rel.b_id) if rel.b_id else None
            c = self.session.get(C, rel.c_id) if rel.c_id else None
            row: dict[str, Any] = {
                "relation_id": rel.id,
                "asset_management_no": rel.asset_management_no,
            }
            row["map_system_name"] = getattr(a, a_attr, None) if a is not None and a_attr else None
            row["map_hyup"] = _b_name(b)
            mp = (rel.relation_meta or {}).get("mapping") or {}
            for col_key, meta_key in (("map_dt", "b_dt"), ("map_ito", "b_ito"), ("map_ops", "b_ops")):
                bid = mp.get(meta_key)
                bb = None
                if bid is not None:
                    try:
                        bb = b_extra.get(int(bid))
                    except (TypeError, ValueError):
                        bb = None
                row[col_key] = _b_name(bb)
            row["map_hostname"] = getattr(c, c_host, None) if c is not None and c_host else None
            row["map_server_cls"] = getattr(c, c_cls, None) if c is not None and c_cls else None
            row["map_ip"] = getattr(c, c_ip, None) if c is not None and c_ip else None
            row["map_port"] = getattr(c, c_port, None) if c is not None and c_port else None
            row["map_server_kind"] = getattr(c, c_kind, None) if c is not None and c_kind else None
            rows_out.append(row)
        return rows_out

    def _c_row_label(self, c: C, k: dict[str, str | None]) -> str:
        parts: list[str] = []
        for attr in (k.get("c_hostname"), k.get("c_server_cls"), k.get("c_ip")):
            if not attr:
                continue
            v = getattr(c, attr, None)
            if v is not None and str(v).strip():
                parts.append(str(v).strip())
        return " · ".join(parts) if parts else f"#{c.id}"

    def _resolve_or_create_a(self, k: dict[str, str | None], pick: str | None, text: str | None) -> int:
        """자산 매핑 UI: 시스템 관리에 등록된 시스템만 선택한다(신규 텍스트 생성 없음)."""
        pid = (pick or "").strip()
        if pid.isdigit():
            return int(pid)
        raise ValueError("시스템명: 시스템 관리 탭에 등록된 시스템명을 선택하세요.")

    def _resolve_or_create_b(
        self,
        k: dict[str, str | None],
        pick: str | None,
        text: str | None,
        role_value: str,
    ) -> int:
        """자산 매핑 UI: 담당자 관리에 등록된 성명만 선택한다(신규 텍스트 생성 없음)."""
        pid = (pick or "").strip()
        if pid.isdigit():
            return int(pid)
        raise ValueError(f"담당자({role_value}): 담당자 관리 탭에 등록된 성명을 선택하세요.")

    def _resolve_or_create_c(
        self,
        k: dict[str, str | None],
        pick: str | None,
        texts: dict[str, str | None],
    ) -> int:
        """자산(C): 기존 행(c_id) 또는 Hostname·서버분류 등 입력으로 매칭/신규 생성."""
        pid = (pick or "").strip()
        if pid.isdigit():
            return int(pid)
        values: dict[str, str | None] = {}
        for form_key, key_k in (
            ("c_server_cls_new", "c_server_cls"),
            ("c_hostname_new", "c_hostname"),
            ("c_ip_new", "c_ip"),
            ("c_port_new", "c_port"),
            ("c_server_kind_new", "c_server_kind"),
        ):
            raw = (texts.get(form_key) or "").strip()
            attr = k.get(key_k)
            if attr and raw:
                values[attr] = raw
        if not values:
            raise ValueError("자산: Hostname·서버분류·IP·Port·서버 구분 중 한 항목 이상 입력하세요.")
        found_id = self._find_c_id_matching_fields(values)
        if found_id is not None:
            return found_id
        obj = self.c_svc.create(values)
        return int(obj.id)

    def _find_c_id_matching_fields(self, values: dict[str, str | None]) -> int | None:
        """입력된 자산 필드(비어 있지 않은 항목만)로 AND 조건에 맞는 C 행을 찾는다."""
        stmt = select(C)
        has = False
        for attr, val in values.items():
            if val is None or not str(val).strip():
                continue
            col = getattr(C, attr, None)
            if col is None:
                continue
            stmt = stmt.where(col == str(val).strip())
            has = True
        if not has:
            return None
        row = self.session.scalar(stmt.order_by(C.id.asc()).limit(1))
        return int(row.id) if row else None

    def create_mapping(
        self,
        *,
        a_pick: str | None,
        a_text: str | None,
        b_picks: dict[str, str | None],
        b_texts: dict[str, str | None],
        c_pick: str | None,
        c_texts: dict[str, str | None],
    ) -> Any:
        k = self._keys()
        a_id = self._resolve_or_create_a(k, a_pick, a_text)

        role_values = {"hyup": "현업", "dt": "DT팀", "ito": "통합ITO", "ops": "운영자"}
        b_ids: dict[str, int] = {}
        for rk, rv in role_values.items():
            b_ids[rk] = self._resolve_or_create_b(k, b_picks.get(rk), b_texts.get(rk), rv)

        primary_b = b_ids["hyup"]
        c_id = self._resolve_or_create_c(k, c_pick, c_texts)

        meta = {
            "mapping": {
                "b_dt": b_ids["dt"],
                "b_ito": b_ids["ito"],
                "b_ops": b_ids["ops"],
            }
        }
        return self.rel_svc.create(a_id, primary_b, c_id, meta)

    @staticmethod
    def form_flat_to_create_kwargs(d: dict[str, Any]) -> dict[str, Any]:
        """HTML 폼에서 넘긴 단일 행 dict → create_mapping / update_mapping 인자."""

        def g(key: str) -> str | None:
            v = d.get(key)
            if v is None:
                return None
            s = str(v).strip()
            return s if s else None

        return {
            "a_pick": g("a_id"),
            "a_text": g("a_system_name_new"),
            "b_picks": {
                "hyup": g("b_hyup_id"),
                "dt": g("b_dt_id"),
                "ito": g("b_ito_id"),
                "ops": g("b_ops_id"),
            },
            "b_texts": {
                "hyup": g("b_hyup_name_new"),
                "dt": g("b_dt_name_new"),
                "ito": g("b_ito_name_new"),
                "ops": g("b_ops_name_new"),
            },
            "c_pick": g("c_id"),
            "c_texts": {
                "c_server_cls_new": g("c_server_cls_new"),
                "c_hostname_new": g("c_hostname_new"),
                "c_ip_new": g("c_ip_new"),
                "c_port_new": g("c_port_new"),
                "c_server_kind_new": g("c_server_kind_new"),
            },
        }

    def create_mapping_from_form(self, d: dict[str, Any]) -> Any:
        kw = self.form_flat_to_create_kwargs(d)
        return self.create_mapping(**kw)

    def update_mapping(self, relation_id: int, d: dict[str, Any]) -> Any:
        """기존 Relation의 A/B/C·부담당자 매핑을 갱신한다. 자산관리번호는 유지한다."""
        kw = self.form_flat_to_create_kwargs(d)
        k = self._keys()
        a_id = self._resolve_or_create_a(k, kw["a_pick"], kw["a_text"])
        role_values = {"hyup": "현업", "dt": "DT팀", "ito": "통합ITO", "ops": "운영자"}
        b_ids: dict[str, int] = {}
        for rk, rv in role_values.items():
            b_ids[rk] = self._resolve_or_create_b(k, kw["b_picks"].get(rk), kw["b_texts"].get(rk), rv)
        primary_b = b_ids["hyup"]
        c_id = self._resolve_or_create_c(k, kw["c_pick"], kw["c_texts"])
        meta = {
            "mapping": {
                "b_dt": b_ids["dt"],
                "b_ito": b_ids["ito"],
                "b_ops": b_ids["ops"],
            }
        }
        return self.rel_svc.update(relation_id, a_id, primary_b, c_id, meta)
