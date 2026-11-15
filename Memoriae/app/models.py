"""Façade de compatibilité des modèles scientifiques et persistants."""

from app.cognitive.patient import Patient
from app.memory import (
    ElementMemoire,
    FeedbackRecuperation,
    Indice,
    ProvenanceSouvenir,
    ResultatRecuperation,
    Souvenir,
    StatutVerification,
    TypeElement,
)
from app.persistence.database import new_id, utc_now
from app.persistence.models import (
    CandidatSouvenir,
    ConfigurationExperience,
    Experience,
    ParticipantAccess,
    ReponseSession,
    ResearcherSession,
    SessionRecuperation,
    SessionTest,
    TentativeRecuperation,
)

__all__ = [
    "CandidatSouvenir", "ConfigurationExperience", "ElementMemoire", "Experience",
    "FeedbackRecuperation", "Indice", "Patient", "ProvenanceSouvenir",
    "ParticipantAccess", "ReponseSession", "ResearcherSession", "ResultatRecuperation", "SessionRecuperation", "SessionTest",
    "Souvenir", "StatutVerification", "TentativeRecuperation", "TypeElement",
    "new_id", "utc_now",
]
