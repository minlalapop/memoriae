from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from app.cognitive.assessment.resultat_test import ResultatTest, resultat_proportion
from app.cognitive.configuration import PARAMETRES_PROTOCOLLES
from app.cognitive.tests.base.test_cognitif import ReponseInvalideError
from app.cognitive.tests.base.test_quiz import TestQuiz
from app.cognitive.tests.progression import parametres_progressifs, taille_grille


class TestMemoireVisuelle(TestQuiz):
    type_test = "memoire_visuelle"
    description = "Test de mémoire visuelle"
    parametres_defaut = PARAMETRES_PROTOCOLLES["memoire_visuelle"]
    progressif = True
    _manifest = json.loads(
        (Path(__file__).parents[1] / "stimuli" / "objets" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    stimuli_version = _manifest["version"]
    _images = [
        {
            "id": image["id"],
            "src": f"/stimuli/objets/{image['fichier']}",
            "label": image["label"],
        }
        for image in _manifest["images"]
    ]

    def generer_essais(self, seed: int, parametres: dict[str, Any]) -> list[dict[str, Any]]:
        return self.generer_bloc(seed, niveau=0, numero=0, parametres=parametres)

    def generer_bloc(
        self,
        seed: int,
        niveau: int,
        numero: int,
        parametres: dict[str, Any],
    ) -> list[dict[str, Any]]:
        mode, difficulte, _, _ = parametres_progressifs(self, parametres)
        lignes, colonnes = taille_grille(niveau, mode, difficulte)
        if lignes * colonnes > len(self._images):
            lignes, colonnes = 3, 3
        capacite = lignes * colonnes
        aleatoire = random.Random(seed + numero * 1019 + niveau * 83)
        propositions = aleatoire.sample(self._images, capacite)
        nombre_cibles = min(max(1, 1 + niveau // 2), max(1, capacite // 2))
        cibles = aleatoire.sample(propositions, nombre_cibles)
        grille = {"lignes": lignes, "colonnes": colonnes}
        return [
            {
                "index": 0,
                "phase": "memorisation",
                "condition": "presentation",
                "stimulus": {
                    "instruction": "Mémorisez les images présentées.",
                    "images": cibles,
                    "stimuli_version": self.stimuli_version,
                },
                "attendu": None,
                "note": False,
                "niveau": niveau,
                "numero_essai": numero,
            },
            {
                "index": 1,
                "phase": "reconnaissance",
                "condition": "reconnaissance_images",
                "stimulus": {
                    "instruction": (
                        f"Sélectionnez les {nombre_cibles} images présentées précédemment."
                    ),
                    "propositions": propositions,
                    "nombre_choix": nombre_cibles,
                    "grille": grille,
                    "stimuli_version": self.stimuli_version,
                },
                "attendu": {"images": [image["id"] for image in cibles]},
                "note": True,
                "niveau": niveau,
                "numero_essai": numero,
            },
        ]

    def evaluer(self, essai: dict[str, Any], reponse: Any) -> ResultatTest:
        if essai["condition"] == "presentation":
            return self._evaluer_presentation(reponse)
        if not isinstance(reponse, dict) or not isinstance(reponse.get("images"), list):
            raise ReponseInvalideError("images doit être une liste")
        images = reponse["images"]
        if not all(isinstance(image, str) for image in images):
            raise ReponseInvalideError("Chaque image doit être identifiée par un texte")
        nombre = essai["stimulus"]["nombre_choix"]
        if len(images) != nombre or len(set(images)) != nombre:
            raise ReponseInvalideError(f"Sélectionnez exactement {nombre} images distinctes")
        propositions = {image["id"] for image in essai["stimulus"]["propositions"]}
        if not set(images) <= propositions:
            raise ReponseInvalideError("La réponse contient une image non proposée")
        attendues = set(essai["attendu"]["images"])
        correctes = len(set(images) & attendues)
        return resultat_proportion(
            correctes,
            nombre,
            {
                "images_correctes": correctes,
                "taille_grille": essai["stimulus"]["grille"],
                "nombre_cibles": nombre,
                "niveau": essai.get("niveau", 0),
                "numero_essai": essai.get("numero_essai", 0),
            },
        )
