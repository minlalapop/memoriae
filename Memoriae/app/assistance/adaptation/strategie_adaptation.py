from dataclasses import dataclass


@dataclass(frozen=True)
class StrategieAdaptation:
    nom: str
    types_prioritaires: list[str]
    justification: str
