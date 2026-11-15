from dataclasses import dataclass

from app.memory.external.souvenir import Souvenir


@dataclass(frozen=True)
class MemoireExterne:
    """Vue métier de la collection de souvenirs persistés d'un patient."""

    patient_id: str
    souvenirs: tuple[Souvenir, ...]

    def rechercher(self, souvenir_id: str) -> Souvenir | None:
        return next(
            (souvenir for souvenir in self.souvenirs if souvenir.id == souvenir_id),
            None,
        )
