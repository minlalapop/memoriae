from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.cognitive.patient import Patient
from app.memory.external.element_memoire import ElementMemoire
from app.memory.external.enums import StatutVerification
from app.memory.external.indice import Indice
from app.memory.external.memoire_externe import MemoireExterne
from app.memory.external.souvenir import Souvenir
from app.persistence import schemas
from app.persistence.database import utc_now


class PatientIntrouvableError(LookupError):
    pass


class SouvenirIntrouvableError(LookupError):
    pass


class GestionnaireMemoire:
    """Opérations métier sur les souvenirs et leur statut de vérification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def ajouter_souvenir(self, patient_id: str, data: schemas.SouvenirCreate) -> Souvenir:
        if self.session.get(Patient, patient_id) is None:
            raise PatientIntrouvableError(patient_id)
        souvenir = Souvenir(
            patient_id=patient_id,
            description=data.description,
            date_evenement=data.date_evenement,
            provenance=data.provenance,
            details_provenance=data.details_provenance,
            statut_verification=data.statut_verification,
            elements=[ElementMemoire(**element.model_dump()) for element in data.elements],
            indices=[Indice(**indice.model_dump()) for indice in data.indices],
        )
        self.session.add(souvenir)
        self.session.commit()
        return self.rechercher_souvenir(souvenir.id)

    def rechercher_souvenir(self, souvenir_id: str) -> Souvenir:
        query = (
            select(Souvenir)
            .options(
                selectinload(Souvenir.elements),
                selectinload(Souvenir.indices),
            )
            .where(Souvenir.id == souvenir_id)
        )
        souvenir = self.session.scalar(query)
        if souvenir is None:
            raise SouvenirIntrouvableError(souvenir_id)
        return souvenir

    def memoire_externe(self, patient_id: str) -> MemoireExterne:
        if self.session.get(Patient, patient_id) is None:
            raise PatientIntrouvableError(patient_id)
        query = (
            select(Souvenir)
            .options(
                selectinload(Souvenir.elements),
                selectinload(Souvenir.indices),
            )
            .where(Souvenir.patient_id == patient_id)
            .order_by(Souvenir.created_at.desc())
        )
        return MemoireExterne(patient_id, tuple(self.session.scalars(query)))

    def lister_souvenirs(self, patient_id: str) -> list[Souvenir]:
        return list(self.memoire_externe(patient_id).souvenirs)

    def modifier_souvenir(
        self, souvenir_id: str, data: schemas.SouvenirUpdate
    ) -> Souvenir:
        souvenir = self.rechercher_souvenir(souvenir_id)
        modifications = data.model_dump(exclude_unset=True, exclude={"indices"})
        for field, value in modifications.items():
            setattr(souvenir, field, value)
        if data.indices is not None:
            souvenir.indices = [Indice(**indice.model_dump()) for indice in data.indices]
        if "statut_verification" in data.model_fields_set:
            if data.statut_verification == StatutVerification.VERIFIE:
                souvenir.verified_at = utc_now()
            else:
                souvenir.source_validation = None
                souvenir.verified_at = None
        self.session.commit()
        return self.rechercher_souvenir(souvenir_id)

    def supprimer_souvenir(self, souvenir_id: str) -> None:
        souvenir = self.rechercher_souvenir(souvenir_id)
        self.session.delete(souvenir)
        self.session.commit()

    def valider_souvenir(
        self, souvenir_id: str, data: schemas.ValidationSouvenir
    ) -> Souvenir:
        souvenir = self.rechercher_souvenir(souvenir_id)
        souvenir.statut_verification = StatutVerification.VERIFIE
        souvenir.source_validation = data.source_validation
        souvenir.verified_at = utc_now()
        self.session.commit()
        return self.rechercher_souvenir(souvenir_id)
