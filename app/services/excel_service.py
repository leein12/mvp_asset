import pandas as pd
from sqlalchemy.orm import Session

from app.services.a_service import AService
from app.services.b_service import BService
from app.services.c_service import CService
from app.services.asset_list_service import ASSET_LIST_COLUMNS, AssetListService
from app.services.d_service import DService
from app.services.field_meta_service import FieldMetaService
from app.utils.field_key_mapping import field_key_to_model_attr


class ExcelService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.field_meta_service = FieldMetaService(session)
        self.service_map = {
            "A": AService(session),
            "B": BService(session),
            "C": CService(session),
            "D": DService(session),
        }

    def export_entity(self, entity_type: str, file_path: str) -> None:
        entity_type = entity_type.upper()
        service = self.service_map[entity_type]
        metas = self.field_meta_service.list_by_entity(entity_type)
        rows = service.list()
        data = []
        for row in rows:
            values = {meta.display_name: getattr(row, field_key_to_model_attr(meta.field_key)) for meta in metas}
            values["id"] = f"{entity_type}{row.id:04d}"
            data.append(values)
        pd.DataFrame(data).to_excel(file_path, index=False)

    def export_asset_list(self, file_path: str) -> None:
        svc = AssetListService(self.session)
        displays = svc.iter_all_items_display()
        rows: list[dict[str, object]] = []
        for d in displays:
            rec: dict[str, object] = {"id": d["id"]}
            for _key, label in ASSET_LIST_COLUMNS:
                rec[label] = d.get(_key)
            rows.append(rec)
        pd.DataFrame(rows).to_excel(file_path, index=False)

    def import_asset_list(self, file_path: str) -> list[str]:
        svc = AssetListService(self.session)
        df = pd.read_excel(file_path)
        errors: list[str] = []
        for index, row in df.iterrows():
            plain: dict[str, object] = {}
            for col in df.columns:
                key = str(col).strip()
                plain[key] = row[col]
            try:
                item_id, form = svc.parse_import_row(plain)
                if item_id is not None:
                    svc.update_from_form(item_id, form)
                else:
                    svc.create_from_form(form)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"row {int(index) + 2}: {exc}")
        return errors

    def import_entity(self, entity_type: str, file_path: str) -> list[str]:
        entity_type = entity_type.upper()
        service = self.service_map[entity_type]
        metas = self.field_meta_service.list_by_entity(entity_type)
        display_to_key = {m.display_name: field_key_to_model_attr(m.field_key) for m in metas}
        df = pd.read_excel(file_path)

        errors: list[str] = []
        for index, row in df.iterrows():
            payload: dict[str, str | None] = {}
            for display, key in display_to_key.items():
                value = row.get(display)
                payload[key] = None if pd.isna(value) else str(value)
            try:
                service.create(payload)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"row {index + 2}: {exc}")
        return errors
