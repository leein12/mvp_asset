from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# REMOVED_ASSET_MAPPING_TAB: relations 마이그레이션은 기존 DB·무결성 점검 호환을 위해 유지.
# UI(/relations)만 제거됨. 리팩터링 시 Relation 모델·테이블·이 마이그레이션 블록을 한 번에 정리.


def _migrate_relations_asset_management_no() -> None:
    """SQLite: add 자산관리번호 column to existing DB and backfill."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(relations)")).fetchall()
        col_names = {r[1] for r in rows}
        if "asset_management_no" in col_names:
            return
        conn.execute(text("ALTER TABLE relations ADD COLUMN asset_management_no VARCHAR(6)"))
        rel_ids = conn.execute(text("SELECT id FROM relations ORDER BY id ASC")).fetchall()
        for idx, (rid,) in enumerate(rel_ids, start=1):
            conn.execute(
                text("UPDATE relations SET asset_management_no = :no WHERE id = :id"),
                {"no": f"{idx:06d}", "id": rid},
            )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_relation_asset_management_no "
                "ON relations(asset_management_no)"
            )
        )


def _migrate_field_meta_in_use() -> None:
    """SQLite: add in_use (사용 여부) for existing field_meta rows."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(field_meta)")).fetchall()
        col_names = {r[1] for r in rows}
        if "in_use" in col_names:
            return
        conn.execute(text("ALTER TABLE field_meta ADD COLUMN in_use BOOLEAN NOT NULL DEFAULT 1"))


def _migrate_field_meta_field_type() -> None:
    """SQLite: is_code → field_type(text|date|code)."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(field_meta)")).fetchall()
        col_names = {r[1] for r in rows}
        if "field_type" in col_names:
            return
        conn.execute(text("ALTER TABLE field_meta ADD COLUMN field_type VARCHAR(10) NOT NULL DEFAULT 'text'"))
        if "is_code" in col_names:
            conn.execute(
                text("UPDATE field_meta SET field_type = CASE WHEN is_code = 1 THEN 'code' ELSE 'text' END")
            )


def _migrate_field_meta_drop_is_code() -> None:
    """SQLite: field_type 도입 후 레거시 is_code 컬럼 제거(NOT NULL로 INSERT 실패 방지)."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(field_meta)")).fetchall()
        col_names = {r[1] for r in rows}
        if "is_code" not in col_names or "field_type" not in col_names:
            return
        conn.execute(text("ALTER TABLE field_meta DROP COLUMN is_code"))


def _migrate_field_meta_field_key_two_digits() -> None:
    """field_meta.field_key를 A00, A01, … 형식으로 통일 (기존 A0, A10 등 정규화)."""
    with engine.begin() as conn:
        rows = list(conn.execute(text("SELECT id, entity_type, field_key FROM field_meta")).fetchall())
        for rid, row_et, fk in rows:
            et = str(row_et or "").strip().upper()
            fk = str(fk or "").strip().upper()
            if et not in ("A", "B", "C", "D") or not fk.startswith(et):
                continue
            suf = fk[len(et) :]
            if not suf.isdigit():
                continue
            n = int(suf)
            new_fk = f"{et}{n:02d}"
            if new_fk != fk:
                conn.execute(
                    text("UPDATE field_meta SET field_key = :nk WHERE id = :id"),
                    {"nk": new_fk, "id": int(rid)},
                )


def _migrate_entity_tables_extra_slots() -> None:
    """SQLite: A/B/C/D 테이블에 값 컬럼 A10–A19 … D10–D19 추가(FieldMeta 슬롯 확장)."""
    letter_tables = (("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"))
    with engine.begin() as conn:
        for table, letter in letter_tables:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            col_names = {str(r[1]) for r in rows}
            for n in range(10, 20):
                col = f"{letter}{n}"
                if col in col_names:
                    continue
                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{col}" VARCHAR(255)'))


def _migrate_code_groups_is_active() -> None:
    """SQLite: 코드 그룹 사용 여부(Admin 코드 상세 필터)."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(code_groups)")).fetchall()
        col_names = {r[1] for r in rows}
        if "is_active" in col_names:
            return
        conn.execute(text("ALTER TABLE code_groups ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))


def _migrate_relations_asset_no_ca_format() -> None:
    """기존 자산관리번호(숫자 등)를 CA00001 형식으로 통일."""
    with engine.begin() as conn:
        rows = list(conn.execute(text("SELECT id, asset_management_no FROM relations ORDER BY id ASC")).fetchall())
        if not rows:
            return

        def _ca_num(s: str) -> int | None:
            t = (s or "").strip().upper()
            if t.startswith("CA") and len(t) > 2 and t[2:].isdigit():
                return int(t[2:])
            return None

        mx = 0
        for (_rid, amn) in rows:
            n = _ca_num(str(amn))
            if n is not None:
                mx = max(mx, n)
        nxt = mx
        for rid, amn in rows:
            if _ca_num(str(amn)) is not None:
                continue
            nxt += 1
            new_no = f"CA{nxt:05d}"
            conn.execute(
                text("UPDATE relations SET asset_management_no = :no WHERE id = :id"),
                {"no": new_no, "id": rid},
            )


def _migrate_purge_all_relations_once() -> None:
    """요청: 기존 자산 매핑(Relation) 데이터를 한 번 비운다(플래그로 1회만)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS _app_migration_flags (name VARCHAR(128) PRIMARY KEY NOT NULL)"
            )
        )
        done = conn.execute(
            text("SELECT 1 FROM _app_migration_flags WHERE name = :n"),
            {"n": "purge_all_relations_asset_list_reset_v1"},
        ).scalar()
        if done:
            return
        conn.execute(text("DELETE FROM relations"))
        conn.execute(
            text("INSERT INTO _app_migration_flags (name) VALUES (:n)"),
            {"n": "purge_all_relations_asset_list_reset_v1"},
        )


def init_db() -> None:
    from app.models import asset_list_item, audit, entities, reference, relation  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_entity_tables_extra_slots()
    _migrate_field_meta_field_key_two_digits()
    _migrate_relations_asset_management_no()
    _migrate_field_meta_in_use()
    _migrate_field_meta_field_type()
    _migrate_field_meta_drop_is_code()
    _migrate_code_groups_is_active()
    _migrate_relations_asset_no_ca_format()
    _migrate_purge_all_relations_once()
