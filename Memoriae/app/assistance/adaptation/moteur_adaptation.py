from typing import Any

from app.assistance.adaptation.strategie_adaptation import StrategieAdaptation
from app.cognitive.assessment.profil_cognitif import ProfilCognitif


class MoteurAdaptation:
    """Choix déterministe d'une stratégie à partir d'observations descriptives."""

    def choisir_strategie(self, profil: ProfilCognitif) -> StrategieAdaptation:
        rappel = profil.performances.get("rappel", {}).get("conditions", {})
        libre = rappel.get("rappel_libre")
        indice = rappel.get("rappel_indice")
        if (
            self._observations_suffisantes(libre)
            and self._observations_suffisantes(indice)
            and indice["score_moyen"] > libre["score_moyen"]
        ):
            return StrategieAdaptation(
                nom="indices_categoriels",
                types_prioritaires=["categorie", "texte", "visuel"],
                justification=(
                    "Au moins deux observations montrent un rappel indicé descriptivement "
                    "supérieur au rappel libre; les indices catégoriels sont essayés en priorité."
                ),
            )
        visuel = profil.performances.get("reconnaissance_visuelle")
        spatial = profil.performances.get("visuospatial")
        if (
            self._observations_suffisantes(visuel)
            and self._observations_suffisantes(spatial)
            and visuel["score_moyen"] >= 0.75
            and spatial["score_moyen"] >= 0.75
        ):
            return StrategieAdaptation(
                nom="indices_visuels",
                types_prioritaires=["visuel", "categorie", "texte"],
                justification=(
                    "Des performances visuelles répétées sont disponibles dans deux tâches; "
                    "cette heuristique expérimentale privilégie les indices visuels sans "
                    "assimiler les scores entre tâches."
                ),
            )
        return StrategieAdaptation(
            nom="equilibree_par_defaut",
            types_prioritaires=[],
            justification=(
                "Données descriptives insuffisantes ou non discriminantes; ordre déterministe "
                "par pertinence et ancienneté."
            ),
        )

    @staticmethod
    def _observations_suffisantes(performance: dict[str, Any] | None) -> bool:
        return bool(performance and performance.get("nombre_essais", 0) >= 2)
