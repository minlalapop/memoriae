"""Compatibilité : utiliser :mod:`app.research` dans le nouveau code."""

from app.research import (
    GestionnaireTests,
    SessionIntrouvableError,
    SoumissionInterditeError,
    TypeTestInconnuError,
)

__all__ = [
    "GestionnaireTests",
    "SessionIntrouvableError",
    "SoumissionInterditeError",
    "TypeTestInconnuError",
]
