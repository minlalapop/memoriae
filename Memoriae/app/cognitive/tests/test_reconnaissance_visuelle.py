from __future__ import annotations

import random
from typing import Any

from app.cognitive.assessment.resultat_test import ResultatTest
from app.cognitive.configuration import PARAMETRES_PROTOCOLLES
from app.cognitive.tests.base.test_cognitif import ReponseInvalideError
from app.cognitive.tests.base.test_quiz import TestQuiz
from app.cognitive.tests.progression import parametres_progressifs, taille_grille


def _matrice_tuple(matrice: list[list[str]]) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(ligne) for ligne in matrice)


class TestReconnaissanceVisuelle(TestQuiz):
    type_test = "reconnaissance_visuelle"
    description = "Test de reconnaissance de symboles"
    parametres_defaut = PARAMETRES_PROTOCOLLES["reconnaissance_visuelle"]
    progressif = True
    _symboles_par_difficulte = {
        "facile": ["●", "▲", "■"],
        "moyen": ["●", "○", "▲", "■", "◆"],
        "difficile": ["●", "○", "▲", "■", "◆", "★", "+", "×"],
    }

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
        symboles = self._symboles_par_difficulte[difficulte]
        nombre_symboles = 1 if difficulte == "facile" else 2
        nombre = self._entier_parametre(parametres, "nombre_propositions", 2, 6)
        lignes, colonnes = taille_grille(niveau, mode, difficulte)
        aleatoire = random.Random(seed + numero * 1013 + niveau * 89)
        cible = self._motif(
            aleatoire, lignes, colonnes, symboles, nombre_symboles
        )
        propositions = [cible]
        deja_vus = {_matrice_tuple(cible)}
        while len(propositions) < nombre:
            candidat = self._motif(
                aleatoire, lignes, colonnes, symboles, nombre_symboles
            )
            cle = _matrice_tuple(candidat)
            if cle not in deja_vus:
                deja_vus.add(cle)
                propositions.append(candidat)
        aleatoire.shuffle(propositions)
        choix = propositions.index(cible)
        grille = {"lignes": lignes, "colonnes": colonnes}
        return [
            {
                "index": 0,
                "phase": "memorisation",
                "condition": "presentation",
                "stimulus": {
                    "instruction": "Mémorisez la disposition des symboles.",
                    "matrice": cible,
                    "grille": grille,
                    "nombre_symboles": nombre_symboles,
                },
                "attendu": None,
                "note": False,
                "niveau": niveau,
                "numero_essai": numero,
            },
            {
                "index": 1,
                "phase": "reconnaissance",
                "condition": "reconnaissance_visuelle",
                "stimulus": {
                    "instruction": "Sélectionnez le motif présenté précédemment.",
                    "propositions": propositions,
                    "grille": grille,
                    "nombre_symboles": nombre_symboles,
                },
                "attendu": {"choix": choix},
                "note": True,
                "niveau": niveau,
                "numero_essai": numero,
            },
        ]

    def evaluer(self, essai: dict[str, Any], reponse: Any) -> ResultatTest:
        if essai["condition"] == "presentation":
            return self._evaluer_presentation(reponse)
        if not isinstance(reponse, dict):
            raise ReponseInvalideError("La réponse doit être un objet JSON")
        choix = reponse.get("choix")
        propositions = essai["stimulus"]["propositions"]
        if (
            isinstance(choix, bool)
            or not isinstance(choix, int)
            or not 0 <= choix < len(propositions)
        ):
            raise ReponseInvalideError("choix doit être l'index d'une proposition")
        correcte = choix == essai["attendu"]["choix"]
        return ResultatTest(
            score=1.0 if correcte else 0.0,
            correcte=correcte,
            mesures={
                "choix_correct": correcte,
                "taille_grille": essai["stimulus"]["grille"],
                "niveau": essai.get("niveau", 0),
                "numero_essai": essai.get("numero_essai", 0),
            },
        )

    def _motif(
        self,
        aleatoire: random.Random,
        lignes: int,
        colonnes: int,
        symboles: list[str],
        nombre_symboles: int,
    ) -> list[list[str]]:
        capacite = lignes * colonnes
        valeurs = [""] * capacite
        for position in aleatoire.sample(range(capacite), nombre_symboles):
            valeurs[position] = aleatoire.choice(symboles)
        return [
            valeurs[index : index + colonnes]
            for index in range(0, len(valeurs), colonnes)
        ]
