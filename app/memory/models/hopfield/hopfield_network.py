from typing import Any

from app.memory.models.memory_model import MemoryModel


class HopfieldNetwork(MemoryModel):
    """Squelette du futur modèle de Hopfield, sans algorithme neuronal."""

    def encode(self, representations: list[Any]) -> None:
        raise NotImplementedError("Le modèle de Hopfield n'est pas encore implémenté")

    def retrieve(self, query: Any, limit: int = 1) -> list[Any]:
        raise NotImplementedError("Le modèle de Hopfield n'est pas encore implémenté")
