from typing import Any

from app.cognitive.tests.base.test_cognitif import TestCognitif

TAILLES_ADAPTATIVES = [(2, 2), (2, 3), (3, 3), (4, 4), (5, 5)]
TAILLES_FIXES = {
    "facile": [(2, 2), (2, 3), (3, 3), (3, 4), (4, 4)],
    "moyen": [(2, 2), (3, 3), (3, 4), (4, 4), (5, 5)],
    "difficile": [(2, 2), (4, 4), (5, 5), (6, 6)],
}


def parametres_progressifs(
    test: TestCognitif, parametres: dict[str, Any]
) -> tuple[str, str, int, int]:
    mode = test._choix_parametre(parametres, "mode", {"adaptatif", "fixe"})
    difficulte = test._choix_parametre(
        parametres, "difficulte", {"facile", "moyen", "difficile"}
    )
    nombre = test._entier_parametre(parametres, "nombre_essais", 3, 10)
    maximum = test._entier_parametre(parametres, "maximum_essais", 3, 10)
    return mode, difficulte, nombre, maximum


def taille_grille(niveau: int, mode: str, difficulte: str) -> tuple[int, int]:
    tailles = TAILLES_ADAPTATIVES if mode == "adaptatif" else TAILLES_FIXES[difficulte]
    return tailles[min(niveau, len(tailles) - 1)]
