from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
LOCAL_ENV_FILE = PROJECT_ROOT / ".env"


def load_local_env() -> None:
    """Charge le fichier local sans dépendance externe.

    Le fichier n'est pas copié dans l'image Docker. En local, il est prioritaire afin qu'une
    ancienne variable exportée dans le terminal ne rende pas la configuration incompréhensible.
    """

    if os.getenv("MEMORIAE_IGNORE_LOCAL_ENV") == "1" or not LOCAL_ENV_FILE.exists():
        return
    for raw_line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key.strip()] = value


load_local_env()
