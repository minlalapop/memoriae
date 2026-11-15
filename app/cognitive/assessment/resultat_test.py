from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResultatTest:
    score: float | None
    correcte: bool | None
    mesures: dict[str, Any]


def resultat_proportion(
    nombre_correct: int, total: int, mesures: dict[str, Any]
) -> ResultatTest:
    score = nombre_correct / total
    return ResultatTest(
        score=score,
        correcte=nombre_correct == total,
        mesures={**mesures, "total": total},
    )
