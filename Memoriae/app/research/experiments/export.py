from __future__ import annotations

import csv
import io
import json
import os
from datetime import date, datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from sqlalchemy.orm import Session

from app.research.experiments.gestionnaire_tests import GestionnaireTests


def exporter_resultats(session: Session, session_id: str, format_export: str) -> tuple[str, str]:
    """Exporte une session sans modifier les données ni recalculer les scores."""
    resultats = GestionnaireTests(session).resultats(session_id)
    enveloppe = {
        "metadata": {
            "export_schema_version": "1.0",
            "code_version": _code_version(),
            "protocol_version": resultats["version"],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        },
        "session": resultats,
    }
    if format_export == "json":
        return json.dumps(enveloppe, ensure_ascii=False, indent=2, default=_json_default), "application/json"
    if format_export == "csv":
        return _vers_csv(enveloppe), "text/csv; charset=utf-8"
    raise ValueError("Format d'export attendu: json ou csv")


def _vers_csv(enveloppe: dict[str, Any]) -> str:
    sortie = io.StringIO()
    session = enveloppe["session"]
    champs = [
        "code_version",
        "protocol_version",
        "session_id",
        "patient_id",
        "protocole",
        "seed",
        "parametres",
        "essai_index",
        "condition",
        "stimulus",
        "reponse",
        "reponse_attendue",
        "score",
        "correcte",
        "mesures",
        "temps_reponse_ms",
        "created_at",
    ]
    writer = csv.DictWriter(sortie, fieldnames=champs)
    writer.writeheader()
    for resultat in session["resultats"]:
        writer.writerow(
            {
                "code_version": enveloppe["metadata"]["code_version"],
                "protocol_version": session["version"],
                "session_id": session["session_id"],
                "patient_id": session["patient_id"],
                "protocole": session["protocole"],
                "seed": session["seed"],
                "parametres": _json_cell(session["parametres"]),
                "essai_index": resultat["essai_index"],
                "condition": resultat["condition"],
                "stimulus": _json_cell(resultat["stimulus"]),
                "reponse": _json_cell(resultat["reponse"]),
                "reponse_attendue": _json_cell(resultat["reponse_attendue"]),
                "score": resultat["score"],
                "correcte": resultat["correcte"],
                "mesures": _json_cell(resultat["mesures"]),
                "temps_reponse_ms": resultat["temps_reponse_ms"],
                "created_at": _json_default(resultat["created_at"]),
            }
        )
    return sortie.getvalue()


def _code_version() -> str:
    configured = os.getenv("MEMORIAE_CODE_VERSION")
    if configured:
        return configured
    try:
        return version("memoriae")
    except PackageNotFoundError:
        return "non-package"


def _json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Type non sérialisable: {type(value).__name__}")
