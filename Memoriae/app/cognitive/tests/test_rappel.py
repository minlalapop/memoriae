from __future__ import annotations

import random
from typing import Any

from app.cognitive.assessment.resultat_test import ResultatTest, resultat_proportion
from app.cognitive.configuration import PARAMETRES_PROTOCOLLES
from app.cognitive.tests.base.test_cognitif import ReponseInvalideError
from app.cognitive.tests.base.test_quiz import TestQuiz


def _normaliser(texte: str) -> str:
    return " ".join(texte.casefold().strip().split())


class TestRappel(TestQuiz):
    type_test = "rappel"
    description = "Test de rappel textuel"
    parametres_defaut = PARAMETRES_PROTOCOLLES["rappel"]

    _items = {
        "facile": [
            ("fruit", "pomme"), ("animal", "cheval"), ("outil", "marteau"),
            ("transport", "train"), ("vêtement", "manteau"), ("meuble", "chaise"),
            ("fleur", "tulipe"), ("instrument", "piano"), ("boisson", "café"),
            ("lieu", "plage"), ("sport", "tennis"), ("objet", "lampe"),
        ],
        "moyen": [
            ("profession", "ingénieur"), ("science", "microscope"),
            ("bâtiment", "bibliothèque"), ("matière", "porcelaine"),
            ("géographie", "archipel"), ("musique", "symphonie"),
            ("médecine", "diagnostic"), ("architecture", "cathédrale"),
            ("technologie", "algorithme"), ("navigation", "boussole"),
            ("littérature", "manuscrit"), ("astronomie", "constellation"),
        ],
        "difficile": [
            ("adjectif", "éphémère"), ("adverbe", "néanmoins"),
            ("grammaire", "subjonctif"), ("rhétorique", "allégorie"),
            ("philosophie", "épistémologie"), ("linguistique", "morphème"),
            ("logique", "syllogisme"), ("sémantique", "polysémie"),
            ("littérature", "anachronisme"), ("syntaxe", "proposition"),
            ("concept", "ambivalence"), ("raisonnement", "inférence"),
        ],
    }
    _distracteurs = {
        "facile": ["poire", "lapin", "tournevis", "bateau", "chemise", "table",
                    "rose", "violon", "thé", "forêt", "football", "horloge"],
        "moyen": ["architecte", "télescope", "université", "marbre", "continent",
                   "concerto", "traitement", "monument", "logiciel", "compas",
                   "ouvrage", "galaxie"],
        "difficile": ["pérenne", "cependant", "indicatif", "métaphore", "ontologie",
                       "phonème", "paradoxe", "synonymie", "chronologie", "complément",
                       "dualité", "déduction"],
    }

    def generer_essais(self, seed: int, parametres: dict[str, Any]) -> list[dict[str, Any]]:
        nombre = self._entier_parametre(parametres, "nombre_items", 2, 8)
        difficulte = self._choix_parametre(
            parametres, "difficulte_mots", {"facile", "moyen", "difficile"}
        )
        aleatoire = random.Random(seed)
        selection = aleatoire.sample(self._items[difficulte], nombre)
        cibles = [item for _, item in selection]
        categories = [categorie for categorie, _ in selection]
        propositions = cibles + aleatoire.sample(self._distracteurs[difficulte], nombre)
        aleatoire.shuffle(propositions)
        association = {categorie: item for categorie, item in selection}
        return [
            {"index": 0, "phase": "memorisation", "condition": "presentation",
             "stimulus": {"instruction": "Mémorisez les mots et leurs catégories.",
                          "elements": [{"categorie": categorie, "item": item}
                                       for categorie, item in selection],
                          "difficulte_mots": difficulte},
             "attendu": None, "note": False},
            {"index": 1, "phase": "rappel_libre", "condition": "rappel_libre",
             "stimulus": {"instruction": "Restituez les éléments mémorisés sans indice.",
                          "nombre_attendu": nombre},
             "attendu": {"items": cibles}, "note": True},
            {"index": 2, "phase": "rappel_indice", "condition": "rappel_indice",
             "stimulus": {"instruction": "Associez un élément à chaque catégorie.",
                          "categories": categories},
             "attendu": {"reponses": association}, "note": True},
            {"index": 3, "phase": "reconnaissance", "condition": "reconnaissance",
             "stimulus": {"instruction": "Sélectionnez les éléments présentés auparavant.",
                          "propositions": propositions, "nombre_choix": nombre},
             "attendu": {"items": cibles}, "note": True},
        ]

    def evaluer(self, essai: dict[str, Any], reponse: Any) -> ResultatTest:
        condition = essai["condition"]
        if condition == "presentation":
            return self._evaluer_presentation(reponse)
        if not isinstance(reponse, dict):
            raise ReponseInvalideError("La réponse doit être un objet JSON")
        if condition == "rappel_libre":
            items = self._liste_textes(reponse.get("items"))
            attendus = {_normaliser(item) for item in essai["attendu"]["items"]}
            trouves = len({_normaliser(item) for item in items} & attendus)
            return resultat_proportion(trouves, len(attendus), {"items_corrects": trouves})
        if condition == "rappel_indice":
            valeurs = reponse.get("reponses")
            if not isinstance(valeurs, dict) or not all(
                isinstance(cle, str) and isinstance(valeur, str)
                for cle, valeur in valeurs.items()
            ):
                raise ReponseInvalideError("reponses doit associer chaque catégorie à un texte")
            attendus = essai["attendu"]["reponses"]
            corrects = sum(
                _normaliser(valeurs.get(categorie, "")) == _normaliser(item)
                for categorie, item in attendus.items()
            )
            return resultat_proportion(corrects, len(attendus), {"indices_corrects": corrects})
        if condition == "reconnaissance":
            items = self._liste_textes(reponse.get("items"))
            nombre = len(essai["attendu"]["items"])
            normalises = [_normaliser(item) for item in items]
            propositions = {_normaliser(item) for item in essai["stimulus"]["propositions"]}
            if len(items) != nombre or len(set(normalises)) != nombre:
                raise ReponseInvalideError(
                    f"Sélectionnez exactement {nombre} propositions distinctes"
                )
            if not set(normalises) <= propositions:
                raise ReponseInvalideError("La réponse contient un élément absent des propositions")
            attendus = {_normaliser(item) for item in essai["attendu"]["items"]}
            corrects = len(set(normalises) & attendus)
            return resultat_proportion(
                corrects, nombre, {"reconnaissances_correctes": corrects}
            )
        raise ReponseInvalideError("Condition de rappel inconnue")

    @staticmethod
    def _liste_textes(valeur: Any) -> list[str]:
        if not isinstance(valeur, list) or not all(isinstance(item, str) for item in valeur):
            raise ReponseInvalideError("items doit être une liste de textes")
        return valeur
