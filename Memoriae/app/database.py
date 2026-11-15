"""Façade de compatibilité de l'infrastructure de persistance."""

from app.persistence.database import (
    DATABASE_URL,
    Base,
    SessionLocal,
    build_engine,
    engine,
    get_session,
    init_db,
    new_id,
    utc_now,
)

__all__ = [
    "DATABASE_URL", "Base", "SessionLocal", "build_engine", "engine", "get_session",
    "init_db", "new_id", "utc_now",
]
