from typing import Any


class ProtocoleEvaluation:
    """Squelette d'un futur protocole comparatif de recherche."""

    def executer(self, configuration: dict[str, Any]) -> Any:
        raise NotImplementedError("Les protocoles d'évaluation ne sont pas encore implémentés")

    def evaluer(self, resultats: list[Any]) -> dict[str, Any]:
        raise NotImplementedError("Les protocoles d'évaluation ne sont pas encore implémentés")
