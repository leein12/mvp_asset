from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "asset_mvp.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

DEFAULT_TEXT_MAX_LENGTH = 255

# 시스템/담당자/자산/도구(A–D)별 FieldMeta·DB 컬럼 슬롯 수 (A0~A{ENTITY_FIELD_SLOT_COUNT-1})
ENTITY_FIELD_SLOT_COUNT = 20

# 목록·Admin 페이징: 허용값 및 기본 페이지 크기
ALLOWED_LIST_PER_PAGE = (20, 50, 100)
DEFAULT_LIST_PER_PAGE = 20
