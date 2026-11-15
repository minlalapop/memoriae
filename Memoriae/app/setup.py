from __future__ import annotations

import getpass
import os
import shutil
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config import LOCAL_ENV_FILE, PROJECT_ROOT, load_local_env
from app.security import hash_password

BASELINE_REVISION = "75d39e02926b"
HEAD_REVISION = "b8e31a6c4f20"
BASELINE_TABLES = {
    "patients",
    "configurations_experience",
    "sessions_test",
    "reponses_session",
}
PLATFORM_TABLES = {"experiences", "participant_access", "researcher_sessions"}


def _write_local_configuration(username: str, password_hash: str) -> None:
    existing: dict[str, str] = {}
    if LOCAL_ENV_FILE.exists():
        for line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                existing[key.strip()] = value.strip()
    existing.setdefault(
        "MEMORIAE_DATABASE_URL",
        os.getenv("MEMORIAE_DATABASE_URL", "sqlite:///data/memoriae.db"),
    )
    existing["MEMORIAE_ENV"] = "development"
    existing["MEMORIAE_RESEARCHER_USERNAME"] = username
    existing["MEMORIAE_RESEARCHER_PASSWORD_HASH"] = f"'{password_hash}'"
    existing.setdefault("MEMORIAE_RESEARCHER_SESSION_HOURS", "8")
    content = "\n".join(f"{key}={value}" for key, value in existing.items()) + "\n"
    LOCAL_ENV_FILE.write_text(content, encoding="utf-8")
    load_local_env()


def _backup_sqlite(database_url: str) -> Path | None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        return None
    database = Path(url.database)
    if not database.is_absolute():
        database = PROJECT_ROOT / database
    if not database.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = database.with_name(f"{database.stem}.backup-{timestamp}{database.suffix}")
    shutil.copy2(database, backup)
    return backup


def _prepare_database() -> Path | None:
    database_url = os.getenv("MEMORIAE_DATABASE_URL", "sqlite:///data/memoriae.db")
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    version = None
    if "alembic_version" in tables:
        with engine.connect() as connection:
            version = connection.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    backup = None
    if tables & BASELINE_TABLES and not version:
        if not BASELINE_TABLES <= tables:
            missing = ", ".join(sorted(BASELINE_TABLES - tables))
            raise RuntimeError(f"Schéma SQLite incomplet, tables manquantes : {missing}")
        backup = _backup_sqlite(database_url)
        command.stamp(config, HEAD_REVISION if PLATFORM_TABLES <= tables else BASELINE_REVISION)
    command.upgrade(config, "head")
    engine.dispose()
    return backup


def main() -> None:
    print("Configuration locale de Memoriae")
    username = input("Identifiant chercheur [chercheur] : ").strip() or "chercheur"
    password = getpass.getpass("Mot de passe chercheur : ")
    confirmation = getpass.getpass("Confirmer le mot de passe : ")
    if password != confirmation:
        raise SystemExit("Les mots de passe ne correspondent pas.")
    try:
        password_hash = hash_password(password)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    _write_local_configuration(username, password_hash)
    backup = _prepare_database()
    print("\nConfiguration terminée.")
    if backup:
        print(f"Sauvegarde de la base : {backup}")
    print("Lancer maintenant : uvicorn app.main:app --reload")
    print(f"Connexion : identifiant « {username} » et le mot de passe saisi.")


if __name__ == "__main__":
    main()
