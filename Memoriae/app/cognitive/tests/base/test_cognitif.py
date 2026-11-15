from abc import ABC, abstractmethod
from typing import Any

from app.cognitive.assessment.resultat_test import ResultatTest
from app.cognitive.configuration import VERSION_PROTOCOLLES


class ReponseInvalideError(ValueError):
    pass


class TestCognitif(ABC):
    """Contrat commun de génération et d'évaluation d'un protocole cognitif."""

    type_test: str
    version = VERSION_PROTOCOLLES
    description: str
    parametres_defaut: dict[str, Any]

    @abstractmethod
    def generer_essais(self, seed: int, parametres: dict[str, Any]) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def evaluer(self, essai: dict[str, Any], reponse: Any) -> ResultatTest:
        pass

    def informations(self) -> dict[str, Any]:
        return {
            "type": self.type_test,
            "version": self.version,
            "description": self.description,
            "parametres_defaut": self.parametres_defaut,
        }

    def _entier_parametre(
        self, parametres: dict[str, Any], nom: str, minimum: int, maximum: int
    ) -> int:
        valeur = parametres.get(nom, self.parametres_defaut[nom])
        if (
            isinstance(valeur, bool)
            or not isinstance(valeur, int)
            or not minimum <= valeur <= maximum
        ):
            raise ReponseInvalideError(
                f"{nom} doit être un entier entre {minimum} et {maximum}"
            )
        inconnus = set(parametres) - set(self.parametres_defaut)
        if inconnus:
            raise ReponseInvalideError(f"Paramètres inconnus: {', '.join(sorted(inconnus))}")
        return valeur

    def _choix_parametre(
        self, parametres: dict[str, Any], nom: str, choix: set[str]
    ) -> str:
        valeur = parametres.get(nom, self.parametres_defaut[nom])
        if not isinstance(valeur, str) or valeur not in choix:
            raise ReponseInvalideError(
                f"{nom} doit être l'une des valeurs: {', '.join(sorted(choix))}"
            )
        inconnus = set(parametres) - set(self.parametres_defaut)
        if inconnus:
            raise ReponseInvalideError(f"Paramètres inconnus: {', '.join(sorted(inconnus))}")
        return valeur

    @staticmethod
    def _evaluer_presentation(reponse: Any) -> ResultatTest:
        if not isinstance(reponse, dict) or reponse.get("continue") is not True:
            raise ReponseInvalideError("La phase de mémorisation attend {'continue': true}")
        return ResultatTest(score=None, correcte=None, mesures={"phase_completee": True})
