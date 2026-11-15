from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from app.cognitive.assessment.resultat_test import ResultatTest
from app.cognitive.configuration import PARAMETRES_PROTOCOLLES
from app.cognitive.tests.base.test_cognitif import ReponseInvalideError
from app.cognitive.tests.base.test_quiz import TestQuiz


class TestAssociatif(TestQuiz):
    """Reconnaissance indicée par une catégorie sémantique contrôlée."""

    type_test = "associatif"
    description = "Mémoire associative et indiçage"
    parametres_defaut = PARAMETRES_PROTOCOLLES["associatif"]
    stimuli_version = "memoriae-objets-v1"
    _categories = {
        "pomme": "fruit",
        "maison": "bâtiment",
        "cle": "objet métallique",
        "velo": "moyen de transport",
        "chat": "animal",
        "ciseaux": "outil",
        "parapluie": "protection contre la pluie",
        "tasse": "récipient",
        "arbre": "végétal",
    }
    _manifest = json.loads(
        (Path(__file__).parents[1] / "stimuli" / "objets" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    _images = [
        {
            "id": image["id"],
            "src": f"/stimuli/objets/{image['fichier']}",
            "label": image["label"],
        }
        for image in _manifest["images"]
    ]

    def generer_essais(self, seed: int, parametres: dict[str, Any]) -> list[dict[str, Any]]:
        nombre = self._entier_parametre(parametres, "nombre_items", 3, 6)
        options = self._entier_parametre(parametres, "nombre_options", 2, nombre)
        duree = self._entier_parametre(parametres, "duree_presentation_ms", 1000, 15000)
        aleatoire = random.Random(seed)
        selection = aleatoire.sample(self._images, nombre)
        ordre_questions = selection[:]
        aleatoire.shuffle(ordre_questions)
        essais = [
            {
                "index": 0,
                "phase": "apprentissage",
                "condition": "presentation",
                "stimulus": {
                    "instruction": "Mémorisez les objets présentés.",
                    "images": selection,
                    "duree_presentation_ms": duree,
                    "stimuli_version": self.stimuli_version,
                },
                "attendu": None,
                "note": False,
            }
        ]
        for index, cible in enumerate(ordre_questions, start=1):
            distracteurs = aleatoire.sample(
                [image for image in selection if image["id"] != cible["id"]],
                options - 1,
            )
            propositions = [cible, *distracteurs]
            aleatoire.shuffle(propositions)
            essais.append(
                {
                    "index": index,
                    "phase": "recuperation",
                    "condition": "reconnaissance_indicee",
                    "stimulus": {
                        "instruction": (
                            "Quel objet appartenait à la catégorie « "
                            f"{self._categories[cible['id']]} » ?"
                        ),
                        "propositions": propositions,
                        "type_indice": "semantique",
                        "strategie_indice": "regles",
                        "stimuli_version": self.stimuli_version,
                    },
                    "attendu": {"choix": cible["id"]},
                    "note": True,
                }
            )
        return essais

    def evaluer(self, essai: dict[str, Any], reponse: Any) -> ResultatTest:
        if essai["condition"] == "presentation":
            return self._evaluer_presentation(reponse)
        if not isinstance(reponse, dict) or not isinstance(reponse.get("choix"), str):
            raise ReponseInvalideError("Un objet doit être sélectionné")
        propositions = {image["id"] for image in essai["stimulus"]["propositions"]}
        if reponse["choix"] not in propositions:
            raise ReponseInvalideError("L'objet sélectionné ne fait pas partie des propositions")
        correcte = reponse["choix"] == essai["attendu"]["choix"]
        return ResultatTest(
            score=1.0 if correcte else 0.0,
            correcte=correcte,
            mesures={
                "type_indice": essai["stimulus"]["type_indice"],
                "strategie_indice": essai["stimulus"]["strategie_indice"],
                "difficulte": len(essai["stimulus"]["propositions"]),
            },
        )
