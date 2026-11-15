"""Compatibilité : utiliser :mod:`app.memory` dans le nouveau code."""

from app.memory import (
    GestionnaireMemoire,
    PatientIntrouvableError,
    SouvenirIntrouvableError,
)

__all__ = [
    "GestionnaireMemoire",
    "PatientIntrouvableError",
    "SouvenirIntrouvableError",
]
