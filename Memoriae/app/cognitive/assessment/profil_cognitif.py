from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfilCognitif:
    patient_id: str
    sessions_terminees: int
    performances: dict[str, dict[str, Any]]
