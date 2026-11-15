import unicodedata
from typing import Any

from app.assistance.adaptation.strategie_adaptation import StrategieAdaptation
from app.memory.external.indice import Indice
from app.memory.models.memory_model import MemoryModel


class SelecteurIndices:
    """Classe et sélectionne un indice sans orchestrer la session de récupération."""

    def __init__(self, memory_model: MemoryModel | None = None) -> None:
        self.memory_model = memory_model

    def selectionner(
        self,
        indices: list[Indice],
        deja_utilises: set[str],
        strategie: StrategieAdaptation,
        niveau_aide: int,
    ) -> tuple[Indice, str] | None:
        disponibles = [indice for indice in indices if indice.id not in deja_utilises]
        if not disponibles:
            return None
        priorites = {
            type_indice: rang for rang, type_indice in enumerate(strategie.types_prioritaires)
        }

        def cle(indice: Indice) -> tuple[Any, ...]:
            type_canonique = _type_canonique(indice.type)
            rang_type = priorites.get(type_canonique, len(priorites))
            pertinence = indice.score_pertinence if indice.score_pertinence is not None else 0.5
            date_creation = indice.created_at.isoformat() if indice.created_at else ""
            if niveau_aide == 0:
                return rang_type, pertinence, date_creation, indice.id
            return -pertinence, rang_type, date_creation, indice.id

        selection = min(disponibles, key=cle)
        if niveau_aide == 0:
            raison = (
                f"Premier indice selon la stratégie {strategie.nom}; type "
                f"{_type_canonique(selection.type)} et pertinence explicite."
            )
        else:
            raison = (
                f"Niveau d'aide {niveau_aide}: indice inutilisé de pertinence élevée, "
                f"pondéré par la stratégie {strategie.nom}."
            )
        return selection, raison


def _type_canonique(type_indice: str) -> str:
    normalise = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", type_indice.casefold())
        if unicodedata.category(caractere) != "Mn"
    )
    if any(mot in normalise for mot in ("image", "photo", "visuel", "spatial")):
        return "visuel"
    if any(mot in normalise for mot in ("categorie", "classe", "semantique")):
        return "categorie"
    return "texte"
