from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import engine
from app.models.entities import A, B, C, D
from app.models.reference import Code, CodeGroup, FieldMeta


def _mflags_table_ensure(conn) -> None:
    conn.execute(
        text("CREATE TABLE IF NOT EXISTS _app_migration_flags (name VARCHAR(128) PRIMARY KEY NOT NULL)")
    )


def _mflags_is_done(name: str) -> bool:
    with engine.begin() as conn:
        _mflags_table_ensure(conn)
        return bool(
            conn.execute(text("SELECT 1 FROM _app_migration_flags WHERE name = :n"), {"n": name}).scalar()
        )


def _mflags_mark_done(name: str) -> None:
    with engine.begin() as conn:
        _mflags_table_ensure(conn)
        conn.execute(text("INSERT OR IGNORE INTO _app_migration_flags (name) VALUES (:n)"), {"n": name})


def seed_defaults(session: Session) -> None:
    _seed_code_groups_and_codes(session)
    _seed_field_meta(session)
    _seed_entities(session)
    _seed_d_five_rows(session)
    # REMOVED_ASSET_MAPPING_TAB: 자산 매핑(Relation) 샘플 시드 비활성. 리팩터링 시 함수 통째로 삭제.
    # _seed_mapping_five_rows(session)


def _seed_code_groups_and_codes(session: Session) -> None:
    status_group = session.scalar(select(CodeGroup).where(CodeGroup.name == "STATUS"))
    if not status_group:
        status_group = CodeGroup(name="STATUS")
        session.add(status_group)
        session.flush()
        for code, label in [("ACTIVE", "Active"), ("INACTIVE", "Inactive"), ("REPAIR", "Repair")]:
            session.add(Code(group_id=status_group.id, code=code, label=label, is_active=True))


def _seed_field_meta(session: Session) -> None:
    status_group = session.scalar(select(CodeGroup).where(CodeGroup.name == "STATUS"))
    if not status_group:
        return
    for entity in ("A", "B", "C", "D"):
        for index in range(10):
            field_key = f"{entity}{index:02d}"
            existing = session.scalar(
                select(FieldMeta).where(FieldMeta.entity_type == entity, FieldMeta.field_key == field_key)
            )
            if existing:
                continue
            field_type = "code" if index == 1 else "text"
            session.add(
                FieldMeta(
                    entity_type=entity,
                    field_key=field_key,
                    in_use=True,
                    display_name=field_key,
                    field_type=field_type,
                    code_group_id=status_group.id if field_type == "code" else None,
                    allow_null=True,
                    max_length=255,
                )
            )


def _seed_entities(session: Session) -> None:
    """최초 1회만 A/B/C/D 샘플 5행. 이후 서버 재기동·삭제 후에도 자동으로 다시 채우지 않는다."""
    if _mflags_is_done("seed_default_entities_v1"):
        return
    has_any = (
        session.scalar(select(A.id).limit(1))
        or session.scalar(select(B.id).limit(1))
        or session.scalar(select(C.id).limit(1))
        or session.scalar(select(D.id).limit(1))
    )
    if has_any:
        _mflags_mark_done("seed_default_entities_v1")
        return
    for i in range(1, 6):
        session.add(A(a0=f"A Name {i}", a1="ACTIVE", a2=f"A Desc {i}"))
        session.add(B(b0=f"B Name {i}", b1="ACTIVE", b2=f"B Desc {i}"))
        session.add(C(c0=f"C Name {i}", c1="ACTIVE", c2=f"C Desc {i}"))
        session.add(D(d0=f"D Name {i}", d1="ACTIVE", d2=f"D Desc {i}"))
    session.flush()
    _mflags_mark_done("seed_default_entities_v1")


def _seed_d_five_rows(session: Session) -> None:
    """도구(D) 샘플 보충은 DB당 최초 1회만. 삭제 후 재기동해도 5행을 맞추지 않는다."""
    if _mflags_is_done("seed_d_five_rows_v1"):
        return
    n = int(session.scalar(select(func.count(D.id))) or 0)
    if n < 5:
        for j in range(n, 5):
            session.add(D(d0=f"도구 기본 {j + 1}", d1="ACTIVE", d2=f"샘플 {j + 1}"))
    _mflags_mark_done("seed_d_five_rows_v1")


# --- REMOVED_ASSET_MAPPING_TAB: 아래 블록 전체·seed_defaults 내 주석 호출 제거 시 삭제 ---
# def _seed_mapping_five_rows(session: Session) -> None:
#     """자산 매핑(Relation) 샘플은 DB당 최초 1회만. 삭제 후에도 5행을 맞추지 않는다."""
#     from app.models.entities import A
#     from app.models.relation import Relation
#     from app.services.asset_mapping_service import AssetMappingService
#     if _mflags_is_done("seed_mapping_five_rows_v1"):
#         return
#     n_rel = int(session.scalar(select(func.count(Relation.id))) or 0)
#     if n_rel >= 5:
#         _mflags_mark_done("seed_mapping_five_rows_v1")
#         return
#     a_rows = list(session.scalars(select(A).order_by(A.id.asc())).all())
#     if not a_rows:
#         _mflags_mark_done("seed_mapping_five_rows_v1")
#         return
#     am = AssetMappingService(session)
#     ctx = am.build_page_context()
#     ro = ctx.get("b_role_options") or {}
#     def _pick_b(rk: str) -> str | None:
#         opts = ro.get(rk) or []
#         return str(opts[0]["id"]) if opts else None
#     b_hyup = _pick_b("hyup")
#     if not b_hyup:
#         _mflags_mark_done("seed_mapping_five_rows_v1")
#         return
#     b_dt, b_ito, b_ops = _pick_b("dt"), _pick_b("ito"), _pick_b("ops")
#     b_dt = b_dt or b_hyup
#     b_ito = b_ito or b_hyup
#     b_ops = b_ops or b_hyup
#     need = 5 - n_rel
#     for k in range(need):
#         idx = n_rel + k + 1
#         a_pick = str(a_rows[(idx - 1) % len(a_rows)].id)
#         am.create_mapping(
#             a_pick=a_pick,
#             a_text=None,
#             b_picks={"hyup": b_hyup, "dt": b_dt, "ito": b_ito, "ops": b_ops},
#             b_texts={"hyup": None, "dt": None, "ito": None, "ops": None},
#             c_pick=None,
#             c_texts={
#                 "c_hostname_new": f"HOST-기본-{idx}",
#                 "c_server_cls_new": f"서버분류-{idx}",
#                 "c_ip_new": f"10.0.0.{idx}",
#                 "c_port_new": str(8000 + idx),
#                 "c_server_kind_new": "샘플구분",
#             },
#         )
#     _mflags_mark_done("seed_mapping_five_rows_v1")
