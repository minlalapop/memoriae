from dataclasses import asdict, dataclass
from statistics import mean


@dataclass(frozen=True)
class ParametresAdaptatifs:
    seuil_progression: float = 0.75
    seuil_baisse: float = 0.5
    fenetre_baisse: int = 2
    baisse_minimale: float = 0.15
    minimum_essais: int = 3
    maximum_essais: int = 8

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionAdaptative:
    continuer: bool
    action: str
    niveau_suivant: int
    raison: str
    moyenne_recente: float

    def as_dict(self) -> dict[str, bool | str | int | float]:
        return asdict(self)


class StrategieAdaptative:
    """Décide de la progression d'une tâche sans interprétation clinique."""

    def __init__(self, parametres: ParametresAdaptatifs | None = None) -> None:
        self.parametres = parametres or ParametresAdaptatifs()
        if self.parametres.fenetre_baisse < 2:
            raise ValueError("fenetre_baisse doit contenir au moins deux essais")
        if self.parametres.minimum_essais < self.parametres.fenetre_baisse + 1:
            raise ValueError("minimum_essais est insuffisant pour détecter une baisse")
        if self.parametres.maximum_essais < self.parametres.minimum_essais:
            raise ValueError("maximum_essais doit être supérieur ou égal à minimum_essais")

    def decider(
        self,
        scores: list[float],
        niveau_actuel: int,
        *,
        mode: str = "adaptatif",
        nombre_essais_fixe: int | None = None,
    ) -> DecisionAdaptative:
        if not scores:
            raise ValueError("Au moins un score est nécessaire")
        if any(score < 0 or score > 1 for score in scores):
            raise ValueError("Les scores doivent être compris entre 0 et 1")

        score = scores[-1]
        moyenne_recente = round(mean(scores[-self.parametres.fenetre_baisse :]), 6)
        if mode == "fixe":
            if nombre_essais_fixe is None or nombre_essais_fixe < 1:
                raise ValueError("nombre_essais_fixe est requis en mode fixe")
            if len(scores) >= nombre_essais_fixe:
                return DecisionAdaptative(
                    False,
                    "arreter_nombre_fixe",
                    niveau_actuel,
                    "Le nombre d'essais prévu est atteint.",
                    moyenne_recente,
                )
            return DecisionAdaptative(
                True,
                "continuer_fixe",
                niveau_actuel + 1,
                "Le prochain essai prévu peut être présenté.",
                moyenne_recente,
            )
        if mode != "adaptatif":
            raise ValueError("Le mode doit être adaptatif ou fixe")

        if len(scores) >= self.parametres.maximum_essais:
            return DecisionAdaptative(
                False,
                "arreter_maximum",
                niveau_actuel,
                "Le nombre maximal d'essais est atteint.",
                moyenne_recente,
            )

        if self._baisse_persistante(scores):
            return DecisionAdaptative(
                False,
                "arreter_baisse_persistante_tache",
                niveau_actuel,
                "Plusieurs essais faibles successifs suivent une performance plus élevée.",
                moyenne_recente,
            )

        if score >= self.parametres.seuil_progression:
            return DecisionAdaptative(
                True,
                "continuer_augmenter",
                niveau_actuel + 1,
                "Le score de l'essai permet une difficulté supérieure.",
                moyenne_recente,
            )
        if score < self.parametres.seuil_baisse:
            return DecisionAdaptative(
                True,
                "continuer_reduire",
                max(0, niveau_actuel - 1),
                "Un essai faible isolé réduit la difficulté sans arrêter la tâche.",
                moyenne_recente,
            )
        return DecisionAdaptative(
            True,
            "continuer_maintenir",
            niveau_actuel,
            "Le niveau est maintenu pour obtenir une observation supplémentaire.",
            moyenne_recente,
        )

    def _baisse_persistante(self, scores: list[float]) -> bool:
        taille = self.parametres.fenetre_baisse
        if len(scores) < self.parametres.minimum_essais:
            return False
        recents = scores[-taille:]
        if not all(score < self.parametres.seuil_baisse for score in recents):
            return False
        precedents = scores[max(0, len(scores) - 2 * taille) : -taille]
        if not precedents:
            return False
        return mean(precedents) - mean(recents) >= self.parametres.baisse_minimale
