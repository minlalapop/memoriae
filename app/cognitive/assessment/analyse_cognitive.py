from typing import Any

from app.cognitive.assessment.profil_cognitif import ProfilCognitif


class AnalyseCognitive:
    """Agrégation arithmétique, sans seuil ni interprétation clinique."""

    def analyser(self, patient_id: str, sessions: list[Any]) -> ProfilCognitif:
        groupes: dict[str, dict[str, list[float]]] = {}
        terminees = 0
        for session in sessions:
            if session.statut != "terminee":
                continue
            terminees += 1
            tache = groupes.setdefault(session.test_type, {})
            for reponse in session.reponses:
                if reponse.score is not None and reponse.condition is not None:
                    tache.setdefault(reponse.condition, []).append(reponse.score)

        performances: dict[str, dict[str, Any]] = {}
        for type_test, conditions in groupes.items():
            tous_scores = [score for scores in conditions.values() for score in scores]
            if not tous_scores:
                continue
            performances[type_test] = {
                "nombre_essais": len(tous_scores),
                "score_moyen": _moyenne(tous_scores),
                "conditions": {
                    condition: {"nombre_essais": len(scores),
                                "score_moyen": _moyenne(scores)}
                    for condition, scores in conditions.items()
                },
            }
        return ProfilCognitif(patient_id, terminees, performances)


def _moyenne(scores: list[float]) -> float:
    return round(sum(scores) / len(scores), 6)
