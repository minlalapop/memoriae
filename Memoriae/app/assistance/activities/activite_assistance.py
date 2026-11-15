from typing import Any


class ActiviteAssistance:
    """Squelette UML d'une future activité d'assistance."""

    def generer_activite(self, contexte: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Les activités d'assistance ne sont pas encore implémentées")

    def evaluer_reponse(self, activite: dict[str, Any], reponse: Any) -> dict[str, Any]:
        raise NotImplementedError("Les activités d'assistance ne sont pas encore implémentées")
