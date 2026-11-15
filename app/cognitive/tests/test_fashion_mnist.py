from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from app.cognitive.assessment.resultat_test import ResultatTest
from app.cognitive.configuration import PARAMETRES_PROTOCOLLES
from app.cognitive.tests.base.test_cognitif import ReponseInvalideError
from app.cognitive.tests.base.test_quiz import TestQuiz


class TestFashionMnist(TestQuiz):
    """Reconnaissance d'une image Fashion-MNIST dont la moitié droite est masquée."""

    type_test = "fashion_mnist_partiel"
    description = "Reconnaissance d’image partielle"
    version = "2.0"
    parametres_defaut = PARAMETRES_PROTOCOLLES["fashion_mnist_partiel"]
    _manifest = json.loads(
        (Path(__file__).parents[1] / "stimuli" / "fashion_mnist" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    stimuli_version = _manifest["version"]
    _images = [
        {
            "id": item["id"],
            "dataset_index": item["dataset_index"],
            "src": f"/stimuli/fashion_mnist/{item['fichier']}",
            "masked_srcs": {
                float(percent) / 100: f"/stimuli/fashion_mnist/{filename}"
                for percent, filename in item["masked_fichiers"].items()
            },
            "label": item["label"],
        }
        for item in _manifest["items"]
    ]

    def generer_essais(self, seed: int, parametres: dict[str, Any]) -> list[dict[str, Any]]:
        legacy = "mask_ratio" in parametres or "nombre_essais" in parametres
        allowed = set(self.parametres_defaut) | {"mask_ratio", "nombre_essais"}
        inconnus = set(parametres) - allowed
        if inconnus:
            raise ReponseInvalideError(f"Paramètres inconnus: {', '.join(sorted(inconnus))}")
        nombre = self._integer(parametres.get("nombre_images", 12), "nombre_images", 4, 12)
        duree = self._integer(
            parametres.get("duree_presentation_ms", 8000),
            "duree_presentation_ms",
            1000,
            30000,
        )
        side = parametres.get("mask_side", "right")
        if side != "right":
            raise ReponseInvalideError("Le masquage doit être appliqué à droite")
        if legacy:
            ratios = [float(parametres.get("mask_ratio", 0.5))]
            trial_counts = [
                self._integer(parametres.get("nombre_essais", 1), "nombre_essais", 1, nombre)
            ]
        else:
            ratios = parametres.get("niveaux_masquage", [0.25, 0.5, 0.75])
            if ratios != [0.25, 0.5, 0.75]:
                raise ReponseInvalideError("Les niveaux doivent être 25 %, 50 % et 75 %")
            essais_par_niveau = self._integer(
                parametres.get("essais_par_niveau", 4), "essais_par_niveau", 4, 4
            )
            if nombre != 12:
                raise ReponseInvalideError("Le protocole utilise exactement 12 images")
            trial_counts = [essais_par_niveau] * len(ratios)

        aleatoire = random.Random(seed)
        selection = aleatoire.sample(self._images, nombre)
        essais = [
            {
                "index": 0,
                "phase": "memorisation",
                "condition": "presentation",
                "stimulus": {
                    "instruction": "Mémorisez les images présentées.",
                    "images": selection,
                    "duree_presentation_ms": duree,
                    "stimuli_version": self.stimuli_version,
                },
                "attendu": None,
                "note": False,
            }
        ]
        targets = aleatoire.sample(selection, sum(trial_counts))
        recognition_trials = []
        target_index = 0
        for ratio, trial_count in zip(ratios, trial_counts):
            for _ in range(trial_count):
                cible = targets[target_index]
                target_index += 1
                distractors = aleatoire.sample(
                    [image for image in selection if image["id"] != cible["id"]], 3
                )
                propositions = [cible, *distractors]
                aleatoire.shuffle(propositions)
                recognition_trials.append(
                    {
                        "phase": "reconnaissance",
                        "condition": "reconnaissance_image_partielle",
                        "stimulus": {
                            "instruction": "Retrouvez l’image dont la partie droite est masquée.",
                            "image_partielle": {
                                "src": cible["masked_srcs"][ratio],
                                "alt": "Image partiellement masquée",
                            },
                            "propositions": propositions,
                            "mask_ratio": ratio,
                            "mask_side": side,
                            "stimuli_version": self.stimuli_version,
                        },
                        "attendu": {"choix": cible["id"]},
                        "note": True,
                    }
                )
        aleatoire.shuffle(recognition_trials)
        for order, trial in enumerate(recognition_trials, start=1):
            trial["index"] = order
            trial["stimulus"]["trial_order"] = order
            essais.append(trial)
        return essais

    @staticmethod
    def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ReponseInvalideError(
                f"{name} doit être un entier entre {minimum} et {maximum}"
            )
        return value

    def evaluer(self, essai: dict[str, Any], reponse: Any) -> ResultatTest:
        if essai["condition"] == "presentation":
            return self._evaluer_presentation(reponse)
        if not isinstance(reponse, dict) or not isinstance(reponse.get("choix"), str):
            raise ReponseInvalideError("Une image doit être sélectionnée")
        propositions = {image["id"] for image in essai["stimulus"]["propositions"]}
        if reponse["choix"] not in propositions:
            raise ReponseInvalideError("L'image sélectionnée ne fait pas partie des propositions")
        correcte = reponse["choix"] == essai["attendu"]["choix"]
        return ResultatTest(
            score=1.0 if correcte else 0.0,
            correcte=correcte,
            mesures={
                "stimulus_id": essai["attendu"]["choix"],
                "reponse_id": reponse["choix"],
                "mask_ratio": essai["stimulus"]["mask_ratio"],
                "mask_side": essai["stimulus"]["mask_side"],
                "trial_order": essai["stimulus"]["trial_order"],
            },
        )
