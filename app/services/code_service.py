from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import Code, CodeGroup
from app.repositories.code_repository import CodeGroupRepository, CodeRepository


class CodeService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.group_repo = CodeGroupRepository(session)
        self.code_repo = CodeRepository(session)

    def list_groups(self) -> list[CodeGroup]:
        return self.group_repo.list_all()

    def list_codes(self, group_id: int | None = None) -> list[Code]:
        if group_id is None:
            stmt = select(Code).order_by(Code.id.asc())
            return list(self.session.scalars(stmt).all())
        return self.code_repo.list_by_group(group_id)

    def list_codes_for_group_ui(self, group_id: int) -> list[Code]:
        """같은 그룹 코드를 id 오름차순(기본값: 가장 작은 id)으로."""
        return self.code_repo.list_by_group_order_id(group_id)

    def create_group(self, name: str, *, is_active: bool = True) -> CodeGroup:
        name = name.strip()
        if not name:
            raise ValueError("그룹명은 필수입니다.")
        if self.group_repo.find_by_name(name):
            raise ValueError("동일한 이름의 코드 그룹이 이미 있습니다.")
        group = CodeGroup(name=name, is_active=is_active)
        self.group_repo.add(group)
        return group

    def update_group(self, group_id: int, name: str, *, is_active: bool) -> CodeGroup:
        name = name.strip()
        if not name:
            raise ValueError(f"그룹 id={group_id}: 그룹명은 필수입니다.")
        obj = self.group_repo.get(group_id)
        if not obj:
            raise ValueError(f"코드 그룹 id={group_id}를 찾을 수 없습니다.")
        other = self.group_repo.find_by_name(name)
        if other and other.id != group_id:
            raise ValueError("다른 그룹에서 이미 사용 중인 이름입니다.")
        obj.name = name
        obj.is_active = is_active
        self.session.flush()
        return obj

    def delete_groups(self, ids: list[int]) -> None:
        from sqlalchemy import select

        from app.models.reference import FieldMeta

        for gid in ids:
            g = self.group_repo.get(gid)
            if not g:
                raise ValueError(f"코드 그룹 id={gid}를 찾을 수 없습니다.")
            metas = list(self.session.scalars(select(FieldMeta).where(FieldMeta.code_group_id == gid)).all())
            for m in metas:
                m.code_group_id = None
                if (m.field_type or "").strip().lower() == "code":
                    m.field_type = "text"
            self.session.delete(g)
        self.session.flush()

    def get_code(self, code_id: int) -> Code | None:
        return self.code_repo.get(code_id)

    def create_code(self, group_id: int, code: str, label: str, is_active: bool = True) -> Code:
        if not self.group_repo.get(group_id):
            raise ValueError("Code group not found.")
        if self.code_repo.find_duplicate_in_group(group_id, code, None):
            raise ValueError("Code already exists in group.")
        obj = Code(group_id=group_id, code=code, label=label, is_active=is_active)
        self.code_repo.add(obj)
        return obj

    def update_code(self, code_id: int, group_id: int, code: str, label: str, is_active: bool) -> Code:
        obj = self.code_repo.get(code_id)
        if not obj:
            raise ValueError("Code not found.")
        if not self.group_repo.get(group_id):
            raise ValueError("Code group not found.")
        if self.code_repo.find_duplicate_in_group(group_id, code.strip(), exclude_id=code_id):
            raise ValueError("같은 그룹에 동일 code가 이미 있습니다.")
        obj.group_id = group_id
        obj.code = code.strip()
        obj.label = label.strip()
        obj.is_active = is_active
        self.session.flush()
        return obj

    def delete_codes(self, ids: list[int]) -> None:
        for cid in ids:
            obj = self.code_repo.get(cid)
            if not obj:
                raise ValueError(f"Code id={cid} not found.")
            self.code_repo.delete(obj)
        self.session.flush()

    def validate_code(self, group_id: int, code: str | None) -> bool:
        if not code:
            return False
        return self.code_repo.find_code(group_id, code) is not None
