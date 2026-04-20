import json
import re
from pathlib import Path
import shutil
import tempfile
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.core.config import ALLOWED_LIST_PER_PAGE, DEFAULT_LIST_PER_PAGE, ENTITY_FIELD_SLOT_COUNT
from app.core.database import SessionLocal
from app.utils.field_key_mapping import field_key_to_model_attr
from app.services.a_service import AService
from app.services.asset_list_service import AssetListService
from app.services.b_service import BService
from app.services.c_service import CService
from app.services.d_service import DService
from app.services.code_service import CodeService
from app.services.excel_service import ExcelService
from app.services.field_meta_service import FieldMetaService
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
templates.env.filters["attr"] = lambda obj, name: getattr(obj, str(name), None)
templates.env.filters["uquote"] = lambda s: quote(str(s or ""), safe="")
templates.env.filters["fk_attr"] = lambda fk: field_key_to_model_attr(str(fk))


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _entity_service(entity_type: str, db: Session):
    service_map = {"A": AService, "B": BService, "C": CService, "D": DService}
    entity_type = entity_type.upper()
    if entity_type not in service_map:
        raise ValueError("Unsupported entity type.")
    return service_map[entity_type](db), entity_type


def _sanitize_per_page(per_page: int) -> int:
    return per_page if per_page in ALLOWED_LIST_PER_PAGE else DEFAULT_LIST_PER_PAGE


_ENTITY_CODE_LABEL_KR = {"A": "시스템", "B": "담당자", "C": "자산", "D": "도구"}


def _sanitize_admin_entity(entity: str | None) -> str:
    e = (entity or "A").strip().upper()
    return e if e in _ENTITY_CODE_LABEL_KR else "A"


def _entity_url(
    entity_type: str,
    *,
    q: str = "",
    page: int = 1,
    per_page: int = DEFAULT_LIST_PER_PAGE,
    error: str | None = None,
    popup: str | None = None,
) -> str:
    params: dict[str, str] = {
        "q": q or "",
        "page": str(max(1, page)),
        "per_page": str(_sanitize_per_page(per_page)),
    }
    if error:
        params["error"] = error
    if popup:
        params["popup"] = popup
    return f"/entities/{entity_type}?{urlencode(params)}"


def _asset_list_url(
    *,
    q: str = "",
    page: int = 1,
    per_page: int = DEFAULT_LIST_PER_PAGE,
    error: str | None = None,
) -> str:
    params: dict[str, str] = {
        "q": q or "",
        "page": str(max(1, page)),
        "per_page": str(_sanitize_per_page(per_page)),
    }
    if error:
        params["error"] = error
    return f"/asset-list?{urlencode(params)}"


_ADMIN_PANELS = frozenset({"groups", "codes", "entity"})


def _sanitize_admin_panel(panel: str | None) -> str:
    p = (panel or "groups").strip().lower()
    return p if p in _ADMIN_PANELS else "groups"


def _admin_url(
    *,
    entity: str = "A",
    groups_page: int = 1,
    groups_per_page: int = DEFAULT_LIST_PER_PAGE,
    codes_page: int = 1,
    codes_per_page: int = DEFAULT_LIST_PER_PAGE,
    metas_page: int = 1,
    metas_per_page: int = DEFAULT_LIST_PER_PAGE,
    panel: str = "groups",
    error: str | None = None,
) -> str:
    params: dict[str, str] = {
        "entity": entity,
        "groups_page": str(max(1, groups_page)),
        "groups_per_page": str(_sanitize_per_page(groups_per_page)),
        "codes_page": str(max(1, codes_page)),
        "codes_per_page": str(_sanitize_per_page(codes_per_page)),
        "metas_page": str(max(1, metas_page)),
        "metas_per_page": str(_sanitize_per_page(metas_per_page)),
        "panel": _sanitize_admin_panel(panel),
    }
    if error:
        params["error"] = error
    return f"/admin?{urlencode(params)}"


def _admin_params_from_form(form) -> dict[str, int | str]:
    """Common query state restored from POST bodies (hidden fields)."""
    return {
        "entity": _sanitize_admin_entity(form.get("entity")),
        "groups_page": max(1, int(form.get("groups_page") or 1)),
        "groups_per_page": _sanitize_per_page(int(form.get("groups_per_page") or DEFAULT_LIST_PER_PAGE)),
        "codes_page": max(1, int(form.get("codes_page") or 1)),
        "codes_per_page": _sanitize_per_page(int(form.get("codes_per_page") or DEFAULT_LIST_PER_PAGE)),
        "metas_page": max(1, int(form.get("metas_page") or 1)),
        "metas_per_page": _sanitize_per_page(int(form.get("metas_per_page") or DEFAULT_LIST_PER_PAGE)),
    }


def _pager_numeric_pages(current: int, total: int) -> list[int | str]:
    """Return page numbers and '__gap__' placeholders for a compact bottom pager."""
    _GAP = "__gap__"
    if total <= 1:
        return [1] if total == 1 else []
    if total <= 9:
        return list(range(1, total + 1))
    out: list[int | str] = []
    window = {1, 2, total - 1, total, current - 1, current, current + 1}
    nums = sorted(n for n in window if 1 <= n <= total)
    prev = 0
    for n in nums:
        if prev and n - prev > 1:
            out.append(_GAP)
        out.append(n)
        prev = n
    return out


@router.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return RedirectResponse(f"/asset-list?page=1&per_page={DEFAULT_LIST_PER_PAGE}", status_code=303)


def _meta_code_options(db: Session, metas: list) -> dict[str, list]:
    from app.services.code_service import CodeService

    svc = CodeService(db)
    out: dict[str, list] = {}
    cache: dict[int, list] = {}
    for m in metas:
        ft = (m.field_type or "text").strip().lower()
        if ft != "code" or not m.code_group_id:
            continue
        gid = int(m.code_group_id)
        if gid not in cache:
            cache[gid] = svc.list_codes_for_group_ui(gid)
        out[field_key_to_model_attr(m.field_key)] = cache[gid]
    return out


@router.get("/entities/{entity_type}", response_class=HTMLResponse)
def entity_page(
    request: Request,
    entity_type: str,
    q: str = "",
    page: int = 1,
    per_page: int = DEFAULT_LIST_PER_PAGE,
    error: str = "",
    popup: str = "",
    db: Session = Depends(get_db),
):
    try:
        service, entity_type = _entity_service(entity_type, db)
    except ValueError:
        return RedirectResponse(f"/entities/A?page=1&per_page={DEFAULT_LIST_PER_PAGE}", status_code=303)
    per_page = _sanitize_per_page(per_page)
    page = max(1, page)
    meta_service = FieldMetaService(db)
    metas = meta_service.list_by_entity(entity_type)
    meta_code_options = _meta_code_options(db, metas)
    all_rows = service.list(q)
    total_rows = len(all_rows)
    max_row_id = max((r.id for r in all_rows), default=0)
    total_pages = max(1, (total_rows + per_page - 1) // per_page) if total_rows else 1
    page = min(page, total_pages)
    start = (page - 1) * per_page
    rows = all_rows[start : start + per_page]
    titles = {"A": "시스템 관리", "B": "담당자 관리", "C": "자산 관리", "D": "도구 관리"}
    return templates.TemplateResponse(
        request,
        "entity.html",
        {
            "entity_type": entity_type,
            "page_title": titles.get(entity_type, f"{entity_type} 관리"),
            "metas": metas,
            "meta_code_options": meta_code_options,
            "max_row_id": max_row_id,
            "rows": rows,
            "query": q,
            "page": page,
            "per_page": per_page,
            "total_rows": total_rows,
            "total_pages": total_pages,
            "error": error,
            "popup": popup,
            "tab": entity_type,
        },
    )


_NEW_ENTITY_ROW_FIELD = re.compile(r"^new_(\d+)_([a-z0-9]+)$", re.I)


@router.post("/entities/{entity_type}/create")
async def create_entity(
    request: Request,
    entity_type: str,
    db: Session = Depends(get_db),
):
    service, entity_type = _entity_service(entity_type, db)
    meta_service = FieldMetaService(db)
    metas = meta_service.list_by_entity(entity_type)
    form = await request.form()
    payload = {
        field_key_to_model_attr(m.field_key): (form.get(field_key_to_model_attr(m.field_key)) or "").strip() or None
        for m in metas
    }
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    try:
        service.create(payload)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


@router.post("/entities/{entity_type}/batch-create")
async def batch_create_entity(request: Request, entity_type: str, db: Session = Depends(get_db)):
    service, entity_type = _entity_service(entity_type, db)
    meta_service = FieldMetaService(db)
    metas = meta_service.list_by_entity(entity_type)
    form = await request.form()
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    rows_by_index: dict[int, dict[str, str | None]] = {}
    for key in form.keys():
        m = _NEW_ENTITY_ROW_FIELD.match(str(key))
        if not m:
            continue
        idx = int(m.group(1))
        fk = m.group(2).lower()
        raw = form.get(key)
        if raw is None:
            rows_by_index.setdefault(idx, {})[fk] = None
        else:
            s = str(raw).strip()
            rows_by_index.setdefault(idx, {})[fk] = s or None
    if not rows_by_index:
        return RedirectResponse(
            _entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error="저장할 신규 행 데이터가 없습니다."),
            status_code=303,
        )
    try:
        for idx in sorted(rows_by_index.keys()):
            row_data = rows_by_index[idx]
            payload = {field_key_to_model_attr(m.field_key): row_data.get(field_key_to_model_attr(m.field_key)) for m in metas}
            service.create(payload)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


@router.post("/entities/{entity_type}/batch-update")
async def batch_update_entity(request: Request, entity_type: str, db: Session = Depends(get_db)):
    service, entity_type = _entity_service(entity_type, db)
    meta_service = FieldMetaService(db)
    metas = meta_service.list_by_entity(entity_type)
    form = await request.form()
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    raw_ids = form.getlist("ids")
    ids = [int(x) for x in raw_ids if str(x).isdigit()]
    if not ids:
        return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error="저장할 행을 선택하세요."), status_code=303)
    try:
        for oid in ids:
            payload: dict[str, str | None] = {}
            for m in metas:
                k = field_key_to_model_attr(m.field_key)
                key = f"f_{oid}_{k}"
                val = form.get(key)
                payload[k] = (val or "").strip() or None
            service.update(oid, payload)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


@router.post("/entities/{entity_type}/batch-delete")
async def batch_delete_entity(request: Request, entity_type: str, db: Session = Depends(get_db)):
    service, entity_type = _entity_service(entity_type, db)
    form = await request.form()
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    ids = [int(x) for x in form.getlist("ids") if str(x).isdigit()]
    if not ids:
        return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error="삭제할 행을 선택하세요."), status_code=303)
    try:
        for oid in ids:
            service.delete(oid)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


@router.get("/entities/{entity_type}/export")
def export_entity(entity_type: str, db: Session = Depends(get_db)):
    _, entity_type = _entity_service(entity_type, db)
    excel = ExcelService(db)
    tmp = tempfile.NamedTemporaryFile(suffix=f"_{entity_type}.xlsx", delete=False)
    tmp.close()
    excel.export_entity(entity_type, tmp.name)
    return FileResponse(
        tmp.name,
        filename=f"{entity_type}_export.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(lambda: Path(tmp.name).unlink(missing_ok=True)),
    )


@router.post("/entities/{entity_type}/import")
async def import_entity(request: Request, entity_type: str, db: Session = Depends(get_db)):
    _, entity_type = _entity_service(entity_type, db)
    form = await request.form()
    upload = form.get("file")
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    if upload is None:
        return RedirectResponse(
            _entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error="파일을 선택하세요."),
            status_code=303,
        )
    excel = ExcelService(db)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    raw = await upload.read()
    with open(tmp.name, "wb") as out:
        out.write(raw)
    try:
        errors = excel.import_entity(entity_type, tmp.name)
        if errors:
            db.rollback()
            return RedirectResponse(
                _entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error=" | ".join(errors[:5])),
                status_code=303,
            )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    return RedirectResponse(_entity_url(entity_type, q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


# --- REMOVED_ASSET_MAPPING_TAB: /relations GET·POST·batch 엔드포인트는 비활성화됨.
# 리팩터링 시 삭제: relations.html, Relation UI 전용 헬퍼, app/deprecated/README_REMOVED_ASSET_MAPPING.md 참고.


def _asset_list_form_dict_for_prefix(form, prefix: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k in form.keys():
        sk = str(k)
        if sk.startswith(prefix):
            out[sk[len(prefix) :]] = str(form.get(k) or "")
    return out


def _new_asset_list_row_indices(form) -> list[int]:
    idxs: set[int] = set()
    for k in form.keys():
        m = re.match(r"^new_(\d+)_", str(k))
        if m:
            idxs.add(int(m.group(1)))
    return sorted(idxs)


@router.get("/api/asset-list/system-suggest")
def asset_list_system_suggest(q: str = "", db: Session = Depends(get_db)):
    return JSONResponse(AssetListService(db).suggest_systems(q))


@router.get("/api/asset-list/b-suggest")
def asset_list_b_suggest(role: str = "", q: str = "", db: Session = Depends(get_db)):
    return JSONResponse(AssetListService(db).suggest_b_by_role(role, q))


@router.get("/api/asset-list/hostname-suggest")
def asset_list_hostname_suggest(q: str = "", db: Session = Depends(get_db)):
    return JSONResponse(AssetListService(db).suggest_hostnames(q))


@router.post("/asset-list/batch-create")
async def asset_list_batch_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    svc = AssetListService(db)
    try:
        for i in _new_asset_list_row_indices(form):
            d = _asset_list_form_dict_for_prefix(form, f"new_{i}_")
            if not any(str(v).strip() for v in d.values()):
                continue
            svc.create_from_form(d)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    return RedirectResponse(_asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


@router.post("/asset-list/batch-update")
async def asset_list_batch_update(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    ids = [int(x) for x in form.getlist("ids") if str(x).isdigit()]
    if not ids:
        return RedirectResponse(
            _asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page, error="저장할 행을 선택하세요."),
            status_code=303,
        )
    svc = AssetListService(db)
    try:
        for item_id in ids:
            d = _asset_list_form_dict_for_prefix(form, f"f_{item_id}_")
            svc.update_from_form(item_id, d)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    return RedirectResponse(_asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


@router.post("/asset-list/batch-delete")
async def asset_list_batch_delete(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    ids = [int(x) for x in form.getlist("ids") if str(x).isdigit()]
    if not ids:
        return RedirectResponse(
            _asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page, error="삭제할 행을 선택하세요."),
            status_code=303,
        )
    svc = AssetListService(db)
    try:
        svc.delete_ids(ids)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    return RedirectResponse(_asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


@router.get("/asset-list/export")
def asset_list_export(db: Session = Depends(get_db)):
    excel = ExcelService(db)
    tmp = tempfile.NamedTemporaryFile(suffix="_asset_list.xlsx", delete=False)
    tmp.close()
    excel.export_asset_list(tmp.name)
    return FileResponse(
        tmp.name,
        filename="asset_list_export.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(lambda: Path(tmp.name).unlink(missing_ok=True)),
    )


@router.post("/asset-list/import")
async def asset_list_import(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    upload = form.get("file")
    ret_q = (form.get("return_q") or "").strip()
    ret_page = int(form.get("return_page") or 1)
    ret_per_page = _sanitize_per_page(int(form.get("return_per_page") or DEFAULT_LIST_PER_PAGE))
    if upload is None:
        return RedirectResponse(
            _asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page, error="파일을 선택하세요."),
            status_code=303,
        )
    excel = ExcelService(db)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    raw = await upload.read()
    with open(tmp.name, "wb") as out:
        out.write(raw)
    try:
        errors = excel.import_asset_list(tmp.name)
        if errors:
            db.rollback()
            return RedirectResponse(
                _asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page, error=" | ".join(errors[:5])),
                status_code=303,
            )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page, error=str(exc)), status_code=303)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    return RedirectResponse(_asset_list_url(q=ret_q, page=ret_page, per_page=ret_per_page), status_code=303)


@router.get("/ai-asset", response_class=HTMLResponse)
def ai_asset_page(request: Request):
    return templates.TemplateResponse(
        request,
        "ai_asset.html",
        {
            "tab": "ai-asset",
            "page_title": "AI 자산관리",
        },
    )


@router.get("/asset-list", response_class=HTMLResponse)
def asset_list_page(
    request: Request,
    page: int = 1,
    per_page: int = DEFAULT_LIST_PER_PAGE,
    q: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    per_page = _sanitize_per_page(per_page)
    page = max(1, page)
    query = (q or "").strip()
    service = AssetListService(db)
    columns = service.column_specs()
    page_rows, total_rows, page = service.list_page_rows(page, per_page, query)
    total_pages = max(1, (total_rows + per_page - 1) // per_page) if total_rows else 1
    alist_ctx = service.build_page_context()
    editable_rows = [{"display": r} for r in page_rows]
    return templates.TemplateResponse(
        request,
        "asset_list.html",
        {
            "tab": "asset-list",
            "page_title": "자산 리스트",
            "columns": columns,
            "editable_rows": editable_rows,
            "alist_ctx": alist_ctx,
            "query": query,
            "page": page,
            "per_page": per_page,
            "total_rows": total_rows,
            "total_pages": total_pages,
            "error": error,
        },
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    entity: str = "A",
    groups_page: int = 1,
    groups_per_page: int = DEFAULT_LIST_PER_PAGE,
    codes_page: int = 1,
    codes_per_page: int = DEFAULT_LIST_PER_PAGE,
    metas_page: int = 1,
    metas_per_page: int = DEFAULT_LIST_PER_PAGE,
    panel: str = Query(default="groups"),
    error: str = Query(default=""),
    db: Session = Depends(get_db),
):
    groups_per_page = _sanitize_per_page(groups_per_page)
    codes_per_page = _sanitize_per_page(codes_per_page)
    metas_per_page = _sanitize_per_page(metas_per_page)
    groups_page = max(1, groups_page)
    codes_page = max(1, codes_page)
    metas_page = max(1, metas_page)
    entity = _sanitize_admin_entity(entity)
    admin_panel = _sanitize_admin_panel(panel)
    code_service = CodeService(db)
    meta_service = FieldMetaService(db)
    groups = code_service.list_groups()
    total_groups = len(groups)
    total_groups_pages = max(1, (total_groups + groups_per_page - 1) // groups_per_page) if total_groups else 1
    groups_page = min(groups_page, total_groups_pages)
    g_start = (groups_page - 1) * groups_per_page
    paged_groups = groups[g_start : g_start + groups_per_page]

    all_codes = code_service.list_codes()
    active_group_ids = {g.id for g in groups if g.is_active}
    codes_for_detail = [c for c in all_codes if c.group_id in active_group_ids]
    code_detail_groups = [g for g in groups if g.is_active]

    all_metas = meta_service.list_by_entity(entity, include_unused=True)
    total_codes = len(codes_for_detail)
    total_codes_pages = max(1, (total_codes + codes_per_page - 1) // codes_per_page) if total_codes else 1
    codes_page = min(codes_page, total_codes_pages)
    c_start = (codes_page - 1) * codes_per_page
    codes = codes_for_detail[c_start : c_start + codes_per_page]
    total_metas = len(all_metas)
    total_metas_pages = max(1, (total_metas + metas_per_page - 1) // metas_per_page) if total_metas else 1
    metas_page = min(metas_page, total_metas_pages)
    m_start = (metas_page - 1) * metas_per_page
    metas = all_metas[m_start : m_start + metas_per_page]

    def _groups_admin_url(**kw: object) -> str:
        return _admin_url(
            entity=str(kw.get("entity", entity)),
            groups_page=int(kw.get("groups_page", groups_page)),
            groups_per_page=int(kw.get("groups_per_page", groups_per_page)),
            codes_page=int(kw.get("codes_page", codes_page)),
            codes_per_page=int(kw.get("codes_per_page", codes_per_page)),
            metas_page=int(kw.get("metas_page", metas_page)),
            metas_per_page=int(kw.get("metas_per_page", metas_per_page)),
            panel="groups",
            error=kw.get("error") if kw.get("error") is not None else None,
        )

    def _codes_admin_url(**kw: object) -> str:
        return _admin_url(
            entity=str(kw.get("entity", entity)),
            groups_page=int(kw.get("groups_page", groups_page)),
            groups_per_page=int(kw.get("groups_per_page", groups_per_page)),
            codes_page=int(kw.get("codes_page", codes_page)),
            codes_per_page=int(kw.get("codes_per_page", codes_per_page)),
            metas_page=int(kw.get("metas_page", metas_page)),
            metas_per_page=int(kw.get("metas_per_page", metas_per_page)),
            panel="codes",
            error=kw.get("error") if kw.get("error") is not None else None,
        )

    def _entity_admin_url(**kw: object) -> str:
        return _admin_url(
            entity=str(kw.get("entity", entity)),
            groups_page=int(kw.get("groups_page", groups_page)),
            groups_per_page=int(kw.get("groups_per_page", groups_per_page)),
            codes_page=int(kw.get("codes_page", codes_page)),
            codes_per_page=int(kw.get("codes_per_page", codes_per_page)),
            metas_page=int(kw.get("metas_page", metas_page)),
            metas_per_page=int(kw.get("metas_per_page", metas_per_page)),
            panel="entity",
            error=kw.get("error") if kw.get("error") is not None else None,
        )

    groups_pager_prev = _groups_admin_url(groups_page=groups_page - 1) if groups_page > 1 else None
    groups_pager_next = _groups_admin_url(groups_page=groups_page + 1) if groups_page < total_groups_pages else None
    groups_pager_items: list[dict[str, object]] = []
    for p in _pager_numeric_pages(groups_page, total_groups_pages):
        if p == "__gap__":
            groups_pager_items.append({"kind": "gap"})
        else:
            pn = int(p)
            groups_pager_items.append(
                {
                    "kind": "page",
                    "num": pn,
                    "url": _groups_admin_url(groups_page=pn),
                    "current": pn == groups_page,
                }
            )

    codes_pager_prev = _codes_admin_url(codes_page=codes_page - 1) if codes_page > 1 else None
    codes_pager_next = _codes_admin_url(codes_page=codes_page + 1) if codes_page < total_codes_pages else None
    codes_pager_items: list[dict[str, object]] = []
    for p in _pager_numeric_pages(codes_page, total_codes_pages):
        if p == "__gap__":
            codes_pager_items.append({"kind": "gap"})
        else:
            pn = int(p)
            codes_pager_items.append(
                {
                    "kind": "page",
                    "num": pn,
                    "url": _codes_admin_url(codes_page=pn),
                    "current": pn == codes_page,
                }
            )

    metas_pager_prev = _entity_admin_url(metas_page=metas_page - 1) if metas_page > 1 else None
    metas_pager_next = _entity_admin_url(metas_page=metas_page + 1) if metas_page < total_metas_pages else None
    metas_pager_items: list[dict[str, object]] = []
    for p in _pager_numeric_pages(metas_page, total_metas_pages):
        if p == "__gap__":
            metas_pager_items.append({"kind": "gap"})
        else:
            pn = int(p)
            metas_pager_items.append(
                {
                    "kind": "page",
                    "num": pn,
                    "url": _entity_admin_url(metas_page=pn),
                    "current": pn == metas_page,
                }
            )

    entity_letters = ("A", "B", "C", "D")
    admin_nav_entities = [
        {
            "letter": letter,
            "label": _ENTITY_CODE_LABEL_KR[letter],
            "url": _admin_url(
                entity=letter,
                groups_page=groups_page,
                groups_per_page=groups_per_page,
                codes_page=codes_page,
                codes_per_page=codes_per_page,
                metas_page=1 if letter != entity else metas_page,
                metas_per_page=metas_per_page,
                panel="entity",
            ),
            "active": admin_panel == "entity" and entity == letter,
        }
        for letter in entity_letters
    ]
    admin_nav_groups_url = _groups_admin_url()
    admin_nav_codes_url = _codes_admin_url()
    admin_nav_entity_root_url = _entity_admin_url()

    response = templates.TemplateResponse(
        request,
        "admin.html",
        {
            "tab": "admin",
            "page_title": "Admin",
            "groups": groups,
            "paged_groups": paged_groups,
            "code_detail_groups": code_detail_groups,
            "codes": codes,
            "metas": metas,
            "entity": entity,
            "entity_label": _ENTITY_CODE_LABEL_KR[entity],
            "admin_panel": admin_panel,
            "admin_nav_groups_url": admin_nav_groups_url,
            "admin_nav_codes_url": admin_nav_codes_url,
            "admin_nav_entity_root_url": admin_nav_entity_root_url,
            "admin_nav_entities": admin_nav_entities,
            "groups_page": groups_page,
            "groups_per_page": groups_per_page,
            "total_groups": total_groups,
            "total_groups_pages": total_groups_pages,
            "groups_pager_prev": groups_pager_prev,
            "groups_pager_next": groups_pager_next,
            "groups_pager_items": groups_pager_items,
            "codes_pager_prev": codes_pager_prev,
            "codes_pager_next": codes_pager_next,
            "codes_pager_items": codes_pager_items,
            "metas_pager_prev": metas_pager_prev,
            "metas_pager_next": metas_pager_next,
            "metas_pager_items": metas_pager_items,
            "error": error,
            "codes_page": codes_page,
            "codes_per_page": codes_per_page,
            "total_codes": total_codes,
            "total_codes_pages": total_codes_pages,
            "metas_page": metas_page,
            "metas_per_page": metas_per_page,
            "total_metas": total_metas,
            "total_metas_pages": total_metas_pages,
            "admin_page_config": {
                "entity": entity,
                "entity_field_slot_count": ENTITY_FIELD_SLOT_COUNT,
                "groups": [{"id": g.id, "name": g.name} for g in code_detail_groups],
            },
        },
    )
    # Avoid 304 / stale HTML: query (?panel=) must always refetch so sidebar selection matches the active pane.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@router.post("/admin/groups/batch-update")
async def batch_update_groups(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    base = _admin_params_from_form(form)
    selected = form.getlist("selected_rows")
    if not selected:
        return RedirectResponse(
            _admin_url(**base, panel="groups", error="저장할 코드 그룹 행을 선택하세요."),
            status_code=303,
        )
    service = CodeService(db)
    try:
        for token in selected:
            tok = str(token).strip()
            if tok.isdigit():
                gid = int(tok)
                name = (form.get(f"group_{gid}_name") or "").strip()
                if not name:
                    raise ValueError(f"코드 그룹 id={gid}: 그룹명은 필수입니다.")
                raw_ia = form.get(f"group_{gid}_is_active")
                is_active = raw_ia is not None and str(raw_ia).lower() in ("true", "1", "on", "yes")
                service.update_group(gid, name, is_active=is_active)
            elif re.fullmatch(r"n\d+", tok):
                t = tok
                name = (form.get(f"group_{t}_name") or "").strip()
                if not name:
                    raise ValueError(f"신규 행({t}): 그룹명은 필수입니다.")
                raw_ia = form.get(f"group_{t}_is_active")
                is_active = raw_ia is not None and str(raw_ia).lower() in ("true", "1", "on", "yes")
                service.create_group(name, is_active=is_active)
            else:
                raise ValueError(f"알 수 없는 행 토큰: {tok!r}")
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            _admin_url(
                **base,
                panel="groups",
                error="코드 그룹 이름이 중복되거나 제약 조건 위반으로 저장할 수 없습니다.",
            ),
            status_code=303,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_admin_url(**base, panel="groups", error=str(exc)), status_code=303)
    return RedirectResponse(_admin_url(**base, panel="groups"), status_code=303)


@router.post("/admin/groups/batch-delete")
async def batch_delete_groups(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    base = _admin_params_from_form(form)
    raw_ids = form.getlist("selected_rows")
    ids = [int(x) for x in raw_ids if str(x).isdigit()]
    if not ids:
        return RedirectResponse(
            _admin_url(**base, panel="groups", error="삭제할 코드 그룹을 선택하세요."),
            status_code=303,
        )
    service = CodeService(db)
    try:
        service.delete_groups(ids)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_admin_url(**base, panel="groups", error=str(exc)), status_code=303)
    return RedirectResponse(_admin_url(**base, panel="groups"), status_code=303)


@router.post("/admin/codes/batch-update")
async def batch_update_codes(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    base = _admin_params_from_form(form)
    selected = form.getlist("selected_rows")
    if not selected:
        return RedirectResponse(
            _admin_url(**base, panel="codes", error="저장할 코드 행을 선택하세요."),
            status_code=303,
        )
    service = CodeService(db)
    try:
        for token in selected:
            tok = str(token).strip()
            if tok.isdigit():
                cid = int(tok)
                raw_gid = (form.get(f"code_{cid}_group_id") or "").strip()
                if not raw_gid:
                    raise ValueError(f"코드 id={cid}: group_id(코드 그룹)을 선택하세요.")
                group_id = int(raw_gid)
                code_val = (form.get(f"code_{cid}_code") or "").strip()
                label_val = (form.get(f"code_{cid}_label") or "").strip()
                if not code_val or not label_val:
                    raise ValueError(f"코드 id={cid}: code·label은 필수입니다.")
                raw_ia = form.get(f"code_{cid}_is_active")
                is_active = raw_ia is not None and str(raw_ia).lower() in ("true", "1", "on", "yes")
                service.update_code(cid, group_id, code_val, label_val, is_active)
            elif re.fullmatch(r"n\d+", tok):
                t = tok
                raw_gid = (form.get(f"code_{t}_group_id") or "").strip()
                if not raw_gid:
                    raise ValueError(f"신규 행({t}): group_id(코드 그룹)을 선택하세요.")
                group_id = int(raw_gid)
                code_val = (form.get(f"code_{t}_code") or "").strip()
                label_val = (form.get(f"code_{t}_label") or "").strip()
                if not code_val or not label_val:
                    raise ValueError(f"신규 행({t}): code·label은 필수입니다.")
                raw_ia = form.get(f"code_{t}_is_active")
                is_active = raw_ia is not None and str(raw_ia).lower() in ("true", "1", "on", "yes")
                service.create_code(group_id, code_val, label_val, is_active)
            else:
                raise ValueError(f"알 수 없는 행 토큰: {tok!r}")
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            _admin_url(
                **base,
                panel="codes",
                error="같은 코드 그룹 안에 동일한 code 값이 이미 있어 저장할 수 없습니다. 다른 행의 code를 먼저 바꾸거나 삭제한 뒤 다시 시도하세요.",
            ),
            status_code=303,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_admin_url(**base, panel="codes", error=str(exc)), status_code=303)
    return RedirectResponse(_admin_url(**base, panel="codes"), status_code=303)


@router.post("/admin/codes/batch-delete")
async def batch_delete_codes(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    base = _admin_params_from_form(form)
    raw_ids = form.getlist("selected_rows")
    ids = [int(x) for x in raw_ids if str(x).isdigit()]
    if not ids:
        return RedirectResponse(
            _admin_url(**base, panel="codes", error="삭제할 코드를 선택하세요."),
            status_code=303,
        )
    service = CodeService(db)
    try:
        service.delete_codes(ids)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_admin_url(**base, panel="codes", error=str(exc)), status_code=303)
    return RedirectResponse(_admin_url(**base, panel="codes"), status_code=303)


@router.post("/admin/field-meta/batch-update")
async def batch_update_field_meta(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    base = _admin_params_from_form(form)
    entity = str(base["entity"])
    service = FieldMetaService(db)
    et = entity.strip().upper()
    selected = form.getlist("selected_rows")
    if not selected:
        return RedirectResponse(
            _admin_url(**base, panel="entity", error="저장할 행을 선택하세요."),
            status_code=303,
        )
    try:
        for token in selected:
            if token.isdigit():
                mid = int(token)
                existing = service.get_meta(mid)
                if not existing or existing.entity_type != et:
                    raise ValueError(f"필드 id={mid}: 현재 Entity와 일치하지 않습니다.")
                display_name = (form.get(f"meta_{mid}_display_name") or "").strip()
                if not display_name:
                    raise ValueError(f"필드 id={mid}: display_name은 필수입니다.")
                field_type = (form.get(f"meta_{mid}_field_type") or "text").strip().lower()
                raw_cg = (form.get(f"meta_{mid}_code_group_id") or "").strip()
                code_group_id = int(raw_cg) if raw_cg and field_type == "code" else None
                allow_null = (form.get(f"meta_{mid}_allow_null") or "true").lower() == "true"
                max_length = int(form.get(f"meta_{mid}_max_length") or 255)
                raw_in = form.get(f"meta_{mid}_in_use")
                in_use = raw_in is not None and str(raw_in).lower() in ("true", "1", "on", "yes")
                service.update_meta(
                    meta_id=mid,
                    display_name=display_name,
                    field_type=field_type,
                    code_group_id=code_group_id,
                    allow_null=allow_null,
                    max_length=max_length,
                    in_use=in_use,
                )
            elif re.fullmatch(r"n\d+", str(token)):
                t = str(token)
                fk = (form.get(f"meta_{t}_field_key") or "").strip().upper()
                display_name = (form.get(f"meta_{t}_display_name") or "").strip()
                if not display_name:
                    raise ValueError(f"신규 행({t}): display_name은 필수입니다.")
                field_type = (form.get(f"meta_{t}_field_type") or "text").strip().lower()
                raw_cg = (form.get(f"meta_{t}_code_group_id") or "").strip()
                code_group_id = int(raw_cg) if raw_cg and field_type == "code" else None
                allow_null = (form.get(f"meta_{t}_allow_null") or "true").lower() == "true"
                max_length = int(form.get(f"meta_{t}_max_length") or 255)
                raw_in = form.get(f"meta_{t}_in_use")
                in_use = raw_in is not None and str(raw_in).lower() in ("true", "1", "on", "yes")
                if not fk:
                    raise ValueError(f"신규 행({t}): field_key가 없습니다.")
                service.create_meta(
                    entity_type=et,
                    field_key=fk,
                    display_name=display_name,
                    field_type=field_type,
                    code_group_id=code_group_id,
                    allow_null=allow_null,
                    max_length=max_length,
                    in_use=in_use,
                )
            else:
                raise ValueError(f"알 수 없는 행 토큰: {token}")
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_admin_url(**base, panel="entity", error=str(exc)), status_code=303)
    return RedirectResponse(_admin_url(**base, panel="entity"), status_code=303)


@router.post("/admin/field-meta/batch-delete")
async def batch_delete_field_meta(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    base = _admin_params_from_form(form)
    entity = str(base["entity"])
    raw_ids = form.getlist("selected_rows")
    ids = [int(x) for x in raw_ids if str(x).isdigit()]
    if not ids:
        return RedirectResponse(
            _admin_url(**base, panel="entity", error="삭제할 필드 메타를 선택하세요."),
            status_code=303,
        )
    service = FieldMetaService(db)
    try:
        service.delete_metas(entity, ids)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return RedirectResponse(_admin_url(**base, panel="entity", error=str(exc)), status_code=303)
    return RedirectResponse(_admin_url(**base, panel="entity"), status_code=303)


