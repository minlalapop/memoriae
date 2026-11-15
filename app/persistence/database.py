import os
import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import load_local_env

load_local_env()


class Base(DeclarativeBase):
    pass


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_engine(url: str, *, echo: bool = False) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, echo=echo)

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


DATABASE_URL = os.getenv("MEMORIAE_DATABASE_URL", "sqlite:///data/memoriae.db")
parsed_url = make_url(DATABASE_URL)
if parsed_url.drivername.startswith("sqlite") and parsed_url.database not in (None, ":memory:"):
    Path(parsed_url.database).parent.mkdir(parents=True, exist_ok=True)
engine = build_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def init_db(target_engine: Engine = engine) -> None:
    """Crée un schéma isolé pour les tests ou la démonstration.

    Les bases applicatives sont gérées par Alembic et ne passent pas par cette fonction.
    """
    from app import models  # noqa: F401 - enregistre les tables dans Base

    Base.metadata.create_all(target_engine)

