# REMOVED_ASSET_MAPPING_TAB (2026)

자산 매핑 탭(`/relations`)과 배치 API를 비활성화했습니다. DB의 `relations` 테이블·`Relation` 모델·무결성 점검(`integrity_service`)은 그대로 두었습니다.

리팩터링 시 한 번에 삭제하면 되는 항목:

- `app/web/templates/relations.html`
- `app/services/asset_mapping_service.py` (자산 리스트는 `mapping_field_meta_keys.py` 사용)
- `app/models/relation.py`, `app/repositories/relation_repository.py`, `app/services/relation_service.py`, `app/schemas/relation.py` — **다른 코드(무결성, DB)와 함께 검토 후**
- `app/core/database.py`의 `_migrate_relations_*`, `_migrate_purge_all_relations_once`
- `app/utils/sample_data.py`의 주석 처리된 `_seed_mapping_five_rows` 블록 및 `seed_defaults` 주석
- `app/web/routes.py`의 `REMOVED_ASSET_MAPPING_TAB` 주석 블록
- `base.html`의 동일 태그 주석
