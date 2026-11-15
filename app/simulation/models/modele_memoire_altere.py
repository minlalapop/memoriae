from typing import Any

from app.memory.models.memory_model import MemoryModel


class ModeleMemoireAltere(MemoryModel):
    """Squelette d'un futur modèle computationnel soumis à une altération."""

    def encode(self, representations: list[Any]) -> None:
        raise NotImplementedError("Le modèle de mémoire altérée n'est pas encore implémenté")

    def retrieve(self, query: Any, limit: int = 1) -> list[Any]:
        raise NotImplementedError("Le modèle de mémoire altérée n'est pas encore implémenté")
