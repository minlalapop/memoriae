from __future__ import annotations

import random
from typing import Any

from app.cognitive.assessment.resultat_test import ResultatTest, resultat_proportion
from app.cognitive.configuration import PARAMETRES_PROTOCOLLES
from app.cognitive.tests.base.test_cognitif import ReponseInvalideError
from app.cognitive.tests.base.test_jeu import TestJeu
from app.cognitive.tests.progression import (
    parametres_progressifs,
    taille_grille,
)


def _position(index: int, colonnes: int) -> dict[str, int]:
    ligne, colonne = divmod(index, colonnes)
    return {"ligne": ligne, "colonne": colonne}


def _position_valide(position: Any, lignes: int, colonnes: int) -> bool:
    return (
        isinstance(position, dict)
        and set(position) == {"ligne", "colonne"}
        and all(
            isinstance(position[cle], int) and not isinstance(position[cle], bool)
            for cle in position
        )
        and 0 <= position["ligne"] < lignes
        and 0 <= position["colonne"] < colonnes
    )


class TestVisuospatial(TestJeu):
    type_test = "visuospatial"
    description = "Test de mémoire de grille"
    parametres_defaut = PARAMETRES_PROTOCOLLES["visuospatial"]
    progressif = True

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
        capacite = lignes * colonnes
        longueur = min(capacite, 2 + niveau)
        aleatoire = random.Random(seed + numero * 1009 + niveau * 97)
        positions = [
            _position(index, colonnes)
            for index in aleatoire.sample(range(capacite), longueur)
        ]
        grille = {"lignes": lignes, "colonnes": colonnes}
        return [
            {
                "index": 0,
                "phase": "memorisation",
                "condition": "presentation",
                "stimulus": {
                    "instruction": "Mémorisez les positions dans leur ordre.",
                    "grille": grille,
                    "sequence": positions,
                },
                "attendu": None,
                "note": False,
                "niveau": niveau,
                "numero_essai": numero,
            },
            {
                "index": 1,
                "phase": "reproduction",
                "condition": "reproduction",
                "stimulus": {
                    "instruction": (
                        f"Reproduisez les {longueur} positions dans le bon ordre."
                    ),
                    "grille": grille,
                    "longueur_sequence": longueur,
                },
                "attendu": {"positions": positions},
                "note": True,
                "niveau": niveau,
                "numero_essai": numero,
            },
        ]

    def evaluer(self, essai: dict[str, Any], reponse: Any) -> ResultatTest:
        if essai["condition"] == "presentation":
            return self._evaluer_presentation(reponse)
        if not isinstance(reponse, dict) or not isinstance(reponse.get("positions"), list):
            raise ReponseInvalideError("positions doit être une liste")
        positions = reponse["positions"]
        attendues = essai["attendu"]["positions"]
        grille = essai["stimulus"]["grille"]
        if len(positions) != len(attendues):
            raise ReponseInvalideError(
                f"La séquence doit contenir {len(attendues)} positions"
            )
        if not all(
            _position_valide(position, grille["lignes"], grille["colonnes"])
            for position in positions
        ):
            raise ReponseInvalideError("Une position est située hors de la grille")
        correctes = sum(
            position == attendu for position, attendu in zip(positions, attendues)
        )
        presentes = sum(position in attendues for position in positions)
        return resultat_proportion(
            correctes,
            len(attendues),
            {
                "positions_au_bon_rang": correctes,
                "positions_presentes": presentes,
                "ordre_exact": positions == attendues,
                "taille_grille": grille,
                "longueur_sequence": len(attendues),
                "niveau": essai.get("niveau", 0),
                "numero_essai": essai.get("numero_essai", 0),
            },
        )
