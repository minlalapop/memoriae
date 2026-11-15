from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.assistance.adaptation.moteur_adaptation import MoteurAdaptation
from app.assistance.adaptation.strategie_adaptation import StrategieAdaptation
from app.assistance.retrieval.errors import (
    AucunIndiceError,
    EtatRecuperationError,
    RecuperationIntrouvableError,
)
from app.assistance.retrieval.selecteur_indices import SelecteurIndices
from app.cognitive.assessment.analyse_cognitive import AnalyseCognitive
from app.cognitive.assessment.profil_cognitif import ProfilCognitif
from app.cognitive.patient import Patient
from app.memory.external.enums import (
    FeedbackRecuperation,
    ProvenanceSouvenir,
    ResultatRecuperation,
    StatutVerification,
)
from app.memory.external.gestionnaire_memoire import GestionnaireMemoire
from app.memory.external.souvenir import Souvenir
from app.memory.models.memory_model import MemoryModel
from app.persistence import models
from app.persistence.database import utc_now


class ServiceRecuperation:
    def __init__(self, session: Session, memory_model: MemoryModel | None = None) -> None:
        self.session = session
        self.gestionnaire_memoire = GestionnaireMemoire(session)
        self.selecteur = SelecteurIndices(memory_model)
        self.adaptation = MoteurAdaptation()

    def demarrer(self, patient_id: str, souvenir_id: str) -> models.SessionRecuperation:
        if self.session.get(Patient, patient_id) is None:
            raise RecuperationIntrouvableError("Patient introuvable")
        try:
            souvenir = self.gestionnaire_memoire.rechercher_souvenir(souvenir_id)
        except LookupError as exc:
            raise RecuperationIntrouvableError("Souvenir introuvable") from exc
        if souvenir.patient_id != patient_id:
            raise RecuperationIntrouvableError("Souvenir introuvable pour ce patient")

        strategie = self.adaptation.choisir_strategie(self._profil(patient_id))
        recuperation = models.SessionRecuperation(
            patient_id=patient_id,
            souvenir_id=souvenir_id,
            strategie=strategie.nom,
            types_prioritaires=strategie.types_prioritaires,
            justification_strategie=strategie.justification,
        )
        self.session.add(recuperation)
        self.session.commit()
        self.session.refresh(recuperation)
        return recuperation

    def obtenir_indice(
        self, patient_id: str, session_id: str
    ) -> models.TentativeRecuperation:
        recuperation = self._recuperation(patient_id, session_id)
        self._exiger_active(recuperation)
        if recuperation.tentatives and recuperation.tentatives[-1].feedback is None:
            return recuperation.tentatives[-1]
        if (
            recuperation.tentatives
            and recuperation.tentatives[-1].feedback == FeedbackRecuperation.RETROUVE
        ):
            raise EtatRecuperationError("Le souvenir est déclaré retrouvé; terminez la session")

        deja_utilises = {
            tentative.indice_id
            for tentative in recuperation.tentatives
            if tentative.indice_id is not None
        }
        niveau_aide = sum(
            tentative.feedback
            in {
                FeedbackRecuperation.NON_RETROUVE,
                FeedbackRecuperation.PARTIEL,
                FeedbackRecuperation.DEMANDE_AIDE,
            }
            for tentative in recuperation.tentatives
        )
        strategie = StrategieAdaptation(
            recuperation.strategie,
            recuperation.types_prioritaires,
            recuperation.justification_strategie,
        )
        choix = self.selecteur.selectionner(
            recuperation.souvenir.indices, deja_utilises, strategie, niveau_aide
        )
        if choix is None:
            raise AucunIndiceError("Aucun nouvel indice disponible")
        indice, raison = choix
        tentative = models.TentativeRecuperation(
            indice_id=indice.id,
            ordre=len(recuperation.tentatives) + 1,
            indice_type=indice.type,
            indice_contenu=indice.contenu,
            niveau_aide=niveau_aide,
            raison_selection=raison,
        )
        recuperation.tentatives.append(tentative)
        self.session.commit()
        self.session.refresh(tentative)
        return tentative

    def enregistrer_feedback(
        self,
        patient_id: str,
        session_id: str,
        tentative_id: str,
        feedback: FeedbackRecuperation,
        reponse_patient: str | None,
        souvenir_evoque: str | None,
    ) -> tuple[models.TentativeRecuperation, models.CandidatSouvenir | None]:
        recuperation = self._recuperation(patient_id, session_id)
        self._exiger_active(recuperation)
        if not recuperation.tentatives or recuperation.tentatives[-1].id != tentative_id:
            raise EtatRecuperationError("Le feedback doit concerner l'indice courant")
        tentative = recuperation.tentatives[-1]
        if tentative.feedback is not None:
            raise EtatRecuperationError("Un feedback a déjà été enregistré pour cet indice")

        tentative.feedback = feedback
        tentative.reponse_patient = reponse_patient
        tentative.responded_at = utc_now()
        candidat = None
        if souvenir_evoque:
            candidat = models.CandidatSouvenir(
                patient_id=patient_id,
                description=souvenir_evoque,
                provenance=ProvenanceSouvenir.PATIENT,
                statut="en_attente_verification",
            )
            recuperation.candidats.append(candidat)
        self.session.commit()
        self.session.refresh(tentative)
        if candidat is not None:
            self.session.refresh(candidat)
        return tentative, candidat

    def terminer(
        self,
        patient_id: str,
        session_id: str,
        resultat: ResultatRecuperation,
    ) -> dict[str, Any]:
        recuperation = self._recuperation(patient_id, session_id)
        self._exiger_active(recuperation)
        if resultat == ResultatRecuperation.RETROUVE and not any(
            tentative.feedback == FeedbackRecuperation.RETROUVE
            for tentative in recuperation.tentatives
        ):
            raise EtatRecuperationError("Aucun feedback n'indique que le souvenir a été retrouvé")
        if (
            resultat == ResultatRecuperation.ASSISTANCE_EXTERNE
            and not recuperation.assistance_externe_consultee
        ):
            raise EtatRecuperationError("La mémoire externe n'a pas été consultée")
        recuperation.statut = "terminee"
        recuperation.resultat_final = resultat
        recuperation.ended_at = utc_now()
        self.session.commit()
        return self.historique(patient_id, session_id)

    def consulter_memoire_externe(self, patient_id: str, session_id: str) -> dict[str, Any]:
        recuperation = self._recuperation(patient_id, session_id)
        souvenir = self.gestionnaire_memoire.rechercher_souvenir(recuperation.souvenir_id)
        if souvenir.patient_id != patient_id:
            raise RecuperationIntrouvableError("Souvenir introuvable pour ce patient")
        recuperation.assistance_externe_consultee = True
        self.session.commit()
        verifie = souvenir.statut_verification == StatutVerification.VERIFIE
        return {
            "souvenir_id": souvenir.id,
            "description": souvenir.description,
            "date_evenement": souvenir.date_evenement,
            "provenance": souvenir.provenance.value,
            "details_provenance": souvenir.details_provenance,
            "statut_verification": souvenir.statut_verification.value,
            "presentation_comme_fait_verifie": verifie,
            "avertissement": (
                "Information explicitement vérifiée dans le prototype."
                if verifie
                else "Information déclarée ou non vérifiée; ne pas la présenter comme certaine."
            ),
            "elements": [
                {"type": element.type.value, "contenu": element.contenu}
                for element in souvenir.elements
            ],
        }

    def historique(self, patient_id: str, session_id: str) -> dict[str, Any]:
        recuperation = self._recuperation(patient_id, session_id)
        return {
            "id": recuperation.id,
            "patient_id": recuperation.patient_id,
            "souvenir_id": recuperation.souvenir_id,
            "statut": recuperation.statut,
            "strategie": recuperation.strategie,
            "types_prioritaires": recuperation.types_prioritaires,
            "justification_strategie": recuperation.justification_strategie,
            "assistance_externe_consultee": recuperation.assistance_externe_consultee,
            "resultat_final": (
                recuperation.resultat_final.value if recuperation.resultat_final else None
            ),
            "started_at": recuperation.started_at,
            "ended_at": recuperation.ended_at,
            "tentatives": [
                {
                    "id": tentative.id,
                    "ordre": tentative.ordre,
                    "indice_id": tentative.indice_id,
                    "indice_type": tentative.indice_type,
                    "indice_contenu": tentative.indice_contenu,
                    "niveau_aide": tentative.niveau_aide,
                    "raison_selection": tentative.raison_selection,
                    "feedback": tentative.feedback.value if tentative.feedback else None,
                    "reponse_patient": tentative.reponse_patient,
                    "presented_at": tentative.presented_at,
                    "responded_at": tentative.responded_at,
                }
                for tentative in recuperation.tentatives
            ],
            "candidats": [
                {
                    "id": candidat.id,
                    "description": candidat.description,
                    "provenance": candidat.provenance.value,
                    "statut": candidat.statut,
                    "created_at": candidat.created_at,
                }
                for candidat in recuperation.candidats
            ],
        }

    def _profil(self, patient_id: str) -> ProfilCognitif:
        query = (
            select(models.SessionTest)
            .options(selectinload(models.SessionTest.reponses))
            .where(models.SessionTest.patient_id == patient_id)
        )
        sessions = list(self.session.scalars(query))
        return AnalyseCognitive().analyser(patient_id, sessions)

    def _recuperation(
        self, patient_id: str, session_id: str
    ) -> models.SessionRecuperation:
        query = (
            select(models.SessionRecuperation)
            .options(
                selectinload(models.SessionRecuperation.tentatives),
                selectinload(models.SessionRecuperation.candidats),
                selectinload(models.SessionRecuperation.souvenir).selectinload(
                    Souvenir.indices
                ),
            )
            .where(
                models.SessionRecuperation.id == session_id,
                models.SessionRecuperation.patient_id == patient_id,
            )
        )
        recuperation = self.session.scalar(query)
        if recuperation is None:
            raise RecuperationIntrouvableError("Session de récupération introuvable")
        return recuperation

    @staticmethod
    def _exiger_active(recuperation: models.SessionRecuperation) -> None:
        if recuperation.statut != "en_cours":
            raise EtatRecuperationError("La session de récupération est terminée")
