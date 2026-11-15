from abc import ABC, abstractmethod
from typing import Any


class MemoryModel(ABC):
    """Interface indépendante pour une future mémoire associative computationnelle."""

    @abstractmethod
    def encode(self, representations: list[Any]) -> None:
        pass

    @abstractmethod
    def retrieve(self, query: Any, limit: int = 1) -> list[Any]:
        pass
