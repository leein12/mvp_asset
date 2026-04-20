"""FieldMeta 기반 A/B/C 속성명 해석. 자산 리스트·(레거시)자산 매핑 UI에서 공통 사용.

REMOVED_ASSET_MAPPING_TAB: 자산 매핑 탭 제거 후에도 자산 리스트 suggest/표시에 필요.
리팩터링 시 relations·AssetMappingService 정리와 함께 이 모듈만 남기거나 FieldMetaService로 흡수 가능.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.field_meta_repository import FieldMetaRepository
from app.utils.field_key_mapping import field_key_to_model_attr

# 자산 리스트 B 역할별 LIKE 힌트 (dt/ito/ops 담당자 필터)
ROLE_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hyup", ("현업",)),
    ("dt", ("DT팀", "DT")),
    ("ito", ("통합ITO팀", "통합ITO")),
    ("ops", ("운영자",)),
)


def _norm_label(s: str) -> str:
    return "".join((s or "").strip().lower().split())


def _resolve_meta_attr(session: Session, entity_type: str, *hints: str) -> str | None:
    hints_raw = tuple(h for h in hints if h and str(h).strip())
    if not hints_raw:
        return None
    hints_norm = [_norm_label(h) for h in hints_raw]

    best_key: str | None = None
    best_score = -1

    for m in FieldMetaRepository(session).list_by_entity(entity_type):
        if not m.in_use:
            continue
        try:
            model_attr = field_key_to_model_attr(m.field_key)
        except ValueError:
            continue
        fk_norm = _norm_label(m.field_key or "")
        dn_norm = _norm_label(m.display_name or "")
        is_generic_label = dn_norm == fk_norm

        score = 0
        for hn in hints_norm:
            if not hn:
                continue
            if not is_generic_label and hn == dn_norm:
                score = max(score, 96)
            if not is_generic_label and len(hn) >= 2 and hn in dn_norm:
                score = max(score, 78 + min(len(hn), 12))
            if not is_generic_label and len(dn_norm) >= 2 and dn_norm in hn:
                score = max(score, 72 + min(len(dn_norm), 12))
            if hn == model_attr:
                score = max(score, 100 if is_generic_label else 82)

        if score > best_score:
            best_score = score
            best_key = model_attr

    return best_key if best_score >= 70 else None


def _fallback_fk(session: Session, entity_type: str, attr_wanted: str) -> str | None:
    want = attr_wanted.strip().lower()
    for m in FieldMetaRepository(session).list_by_entity(entity_type):
        if not m.in_use:
            continue
        try:
            if field_key_to_model_attr(m.field_key) == want:
                return want
        except ValueError:
            continue
    return None


def mapping_field_keys(session: Session) -> dict[str, str | None]:
    """자산 리스트·매핑에서 사용하는 FieldMeta 기준 ORM 속성명."""
    s = session
    return {
        "a_system": _resolve_meta_attr(s, "A", "시스템 명", "시스템명", "시스템") or _fallback_fk(s, "A", "a0"),
        "b_role": _resolve_meta_attr(s, "B", "역할") or _fallback_fk(s, "B", "b1"),
        "b_name": _resolve_meta_attr(s, "B", "성명", "이름") or _fallback_fk(s, "B", "b0"),
        "c_server_cls": _resolve_meta_attr(s, "C", "서버분류", "서버 분류") or _fallback_fk(s, "C", "c0"),
        "c_hostname": _resolve_meta_attr(s, "C", "hostname", "호스트") or _fallback_fk(s, "C", "c1"),
        "c_ip": _resolve_meta_attr(s, "C", "ip") or _fallback_fk(s, "C", "c2"),
        "c_port": _resolve_meta_attr(s, "C", "port") or _fallback_fk(s, "C", "c3"),
        "c_server_kind": _resolve_meta_attr(s, "C", "서버 구분", "서버구분") or _fallback_fk(s, "C", "c4"),
    }
