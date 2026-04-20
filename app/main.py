import uvicorn

from app.core.database import SessionLocal, init_db
from app.utils.sample_data import seed_defaults
from app.web.app import app


def bootstrap() -> None:
    init_db()
    session = SessionLocal()
    try:
        seed_defaults(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    bootstrap()
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
