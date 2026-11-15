from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.cognitive import (
    TESTS_DISPONIBLES,
    AnalyseCognitive,
)
from app.cognitive.adaptation import ParametresAdaptatifs, StrategieAdaptative
from app.cognitive.patient import Patient
from app.persistence import models, schemas
from app.persistence.database import utc_now


class SessionIntrouvableError(LookupError):
    pass


class TypeTestInconnuError(ValueError):
    pass


class SoumissionInterditeError(ValueError):
    pass


class GestionnaireTests:
    def __init__(self, session: Session) -> None:
        self.session = session

    def lister_tests(self) -> list[dict[str, Any]]:
        return [test.informations() for test in TESTS_DISPONIBLES.values()]

    def demarrer(self, data: schemas.SessionTestCreate) -> models.SessionTest:
        if self.session.get(Patient, data.patient_id) is None:
            raise SessionIntrouvableError("Patient introuvable")
        test = TESTS_DISPONIBLES.get(data.type_test)
        if test is None:
            raise TypeTestInconnuError(data.type_test)
        parametres_effectifs = {**test.parametres_defaut, **data.parametres}
        essais = test.generer_essais(data.seed, parametres_effectifs)
        if getattr(test, "progressif", False):
            parametres_algorithme = ParametresAdaptatifs(
                maximum_essais=int(parametres_effectifs["maximum_essais"])
            )
            parametres_effectifs = {
                **parametres_effectifs,
                "algorithme_adaptatif": parametres_algorithme.as_dict(),
            }
        if hasattr(test, "stimuli_version"):
            parametres_effectifs["stimuli_version"] = test.stimuli_version
        configuration = models.ConfigurationExperience(
            nom=data.protocole,
            version=test.version,
            parametres={
                "type_test": test.type_test,
                "seed": data.seed,
                **parametres_effectifs,
            },
        )
        session_test = models.SessionTest(
            patient_id=data.patient_id,
            configuration=configuration,
            test_type=test.type_test,
            test_version=test.version,
            seed=data.seed,
            statut="en_cours",
            essai_courant=0,
            essais=essais,
        )
        self.session.add(session_test)
        self.session.commit()
        self.session.refresh(session_test)
        return session_test

    def essai_courant(self, session_id: str) -> dict[str, Any] | None:
        session_test = self._session(session_id)
        if session_test.statut == "terminee":
            return None
        return {
            "session_id": session_test.id,
            "test_type": session_test.test_type,
            "version": session_test.test_version,
            **self._essai_public(session_test.essais[session_test.essai_courant]),
        }

    def soumettre(
        self, session_id: str, data: schemas.SoumissionEssai
    ) -> tuple[models.SessionTest, models.ReponseSession]:
        session_test = self._session(session_id)
        if session_test.statut == "terminee":
            raise SoumissionInterditeError("La session est déjà terminée")
        if data.essai_index != session_test.essai_courant:
            raise SoumissionInterditeError("L'essai soumis n'est pas l'essai courant")
        deja_soumise = self.session.scalar(
            select(models.ReponseSession).where(
                models.ReponseSession.session_id == session_id,
                models.ReponseSession.essai_index == data.essai_index,
            )
        )
        if deja_soumise is not None:
            raise SoumissionInterditeError("Une réponse existe déjà pour cet essai")

        essai = session_test.essais[data.essai_index]
        test = TESTS_DISPONIBLES[session_test.test_type]
        resultat = test.evaluer(essai, data.reponse)
        mesures = dict(resultat.mesures)
        if resultat.score is not None and getattr(test, "progressif", False):
            scores_precedents = list(
                self.session.scalars(
                    select(models.ReponseSession.score)
                    .where(
                        models.ReponseSession.session_id == session_id,
                        models.ReponseSession.score.is_not(None),
                    )
                    .order_by(models.ReponseSession.essai_index)
                )
            )
            scores = [float(score) for score in scores_precedents]
            scores.append(resultat.score)
            parametres = session_test.configuration.parametres
            parametres_algorithme = ParametresAdaptatifs(
                **parametres["algorithme_adaptatif"]
            )
            decision = StrategieAdaptative(parametres_algorithme).decider(
                scores,
                int(essai.get("niveau", 0)),
                mode=str(parametres["mode"]),
                nombre_essais_fixe=int(parametres["nombre_essais"]),
            )
            mesures.update(
                {
                    "pourcentage_rappel": round(resultat.score * 100, 2),
                    "decision_progression": decision.as_dict(),
                    "parametres_algorithme": parametres_algorithme.as_dict(),
                }
            )
            if decision.continuer:
                nouveau_bloc = test.generer_bloc(
                    session_test.seed,
                    decision.niveau_suivant,
                    len(scores),
                    {
                        cle: valeur
                        for cle, valeur in parametres.items()
                        if cle in test.parametres_defaut
                    },
                )
                debut = len(session_test.essais)
                nouveaux_essais = [
                    {**nouvel_essai, "index": debut + position}
                    for position, nouvel_essai in enumerate(nouveau_bloc)
                ]
                session_test.essais = [*session_test.essais, *nouveaux_essais]
        reponse = models.ReponseSession(
            session_id=session_id,
            essai_index=data.essai_index,
            condition=essai["condition"],
            stimulus_ref=f"{session_test.test_type}:{data.essai_index}",
            stimulus=essai["stimulus"],
            contenu=json.dumps(data.reponse, ensure_ascii=False, separators=(",", ":")),
            reponse_attendue=essai["attendu"],
            score=resultat.score,
            correcte=resultat.correcte,
            mesures=mesures,
            temps_reponse_ms=data.temps_reponse_ms,
        )
        self.session.add(reponse)
        session_test.essai_courant += 1
        if session_test.essai_courant == len(session_test.essais):
            session_test.statut = "terminee"
            session_test.ended_at = utc_now()
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise SoumissionInterditeError("Une réponse existe déjà pour cet essai") from exc
        self.session.refresh(reponse)
        return session_test, reponse

    def resultats(self, session_id: str) -> dict[str, Any]:
        session_test = self._session_avec_reponses(session_id)
        terminee = session_test.statut == "terminee"
        return {
            "session_id": session_test.id,
            "patient_id": session_test.patient_id,
            "protocole_id": session_test.configuration_id,
            "protocole": session_test.configuration.nom,
            "type_test": session_test.test_type,
            "version": session_test.test_version,
            "seed": session_test.seed,
            "parametres": session_test.configuration.parametres,
            "statut": session_test.statut,
            "started_at": session_test.started_at,
            "ended_at": session_test.ended_at,
            "resultats": [
                {
                    "essai_index": reponse.essai_index,
                    "condition": reponse.condition,
                    "stimulus": reponse.stimulus if terminee else None,
                    "reponse": self._contenu_json(reponse.contenu),
                    "reponse_attendue": reponse.reponse_attendue if terminee else None,
                    "score": reponse.score,
                    "correcte": reponse.correcte,
                    "mesures": reponse.mesures or {},
                    "temps_reponse_ms": reponse.temps_reponse_ms,
                    "created_at": reponse.created_at,
                }
                for reponse in session_test.reponses
            ],
        }

    def profil(self, patient_id: str) -> dict[str, Any]:
        if self.session.get(Patient, patient_id) is None:
            raise SessionIntrouvableError("Patient introuvable")
        query = (
            select(models.SessionTest)
            .options(selectinload(models.SessionTest.reponses))
            .where(models.SessionTest.patient_id == patient_id)
        )
        sessions = list(self.session.scalars(query))
        profil = AnalyseCognitive().analyser(patient_id, sessions)
        return {
            "patient_id": profil.patient_id,
            "sessions_terminees": profil.sessions_terminees,
            "performances": profil.performances,
            "avertissement": (
                "Synthèse descriptive expérimentale uniquement; aucune interprétation "
                "diagnostique ou clinique."
            ),
        }

    def _session(self, session_id: str) -> models.SessionTest:
        session_test = self.session.get(models.SessionTest, session_id)
        if session_test is None:
            raise SessionIntrouvableError("Session introuvable")
        return session_test

    def _session_avec_reponses(self, session_id: str) -> models.SessionTest:
        query = (
            select(models.SessionTest)
            .options(
                selectinload(models.SessionTest.reponses),
                selectinload(models.SessionTest.configuration),
            )
            .where(models.SessionTest.id == session_id)
        )
        session_test = self.session.scalar(query)
        if session_test is None:
            raise SessionIntrouvableError("Session introuvable")
        return session_test

    @staticmethod
    def _essai_public(essai: dict[str, Any]) -> dict[str, Any]:
        return {
            "essai_index": essai["index"],
            "phase": essai["phase"],
            "condition": essai["condition"],
            "stimulus": essai["stimulus"],
        }

    @staticmethod
    def _contenu_json(contenu: str) -> Any:
        try:
            return json.loads(contenu)
        except (json.JSONDecodeError, TypeError):
            return contenu
