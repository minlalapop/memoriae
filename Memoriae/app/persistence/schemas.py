from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.memory.external.enums import (
    FeedbackRecuperation,
    ProvenanceSouvenir,
    ResultatRecuperation,
    StatutVerification,
    TypeElement,
)


class PatientCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=200)
    prenom: str | None = Field(default=None, max_length=200)
    age: int | None = Field(default=None, ge=0, le=130)
    est_fictif: bool = False
    consentement: bool = False
    date_consentement: datetime | None = None

    @model_validator(mode="after")
    def consent_is_consistent(self):
        if self.date_consentement is not None and not self.consentement:
            raise ValueError("Une date de consentement exige un consentement explicite")
        return self


class PatientUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=200)
    prenom: str | None = Field(default=None, max_length=200)
    age: int | None = Field(default=None, ge=0, le=130)
    consentement: bool | None = None
    date_consentement: datetime | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self):
        for field in ("nom", "consentement"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} ne peut pas être nul")
        return self


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nom: str
    prenom: str | None
    age: int | None
    est_fictif: bool
    archived_at: datetime | None
    consentement: bool
    date_consentement: datetime | None
    created_at: datetime
    updated_at: datetime


class ElementCreate(BaseModel):
    type: TypeElement
    contenu: str = Field(min_length=1)


class ElementRead(ElementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class IndiceCreate(BaseModel):
    type: str = Field(min_length=1, max_length=100)
    contenu: str = Field(min_length=1)
    score_pertinence: float | None = Field(default=None, ge=0, le=1)


class IndiceRead(IndiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class SouvenirCreate(BaseModel):
    description: str = Field(min_length=1)
    date_evenement: date | None = None
    provenance: ProvenanceSouvenir
    details_provenance: str | None = Field(default=None, max_length=500)
    statut_verification: StatutVerification = StatutVerification.NON_VERIFIE
    elements: list[ElementCreate] = Field(default_factory=list)
    indices: list[IndiceCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def cannot_self_verify(self):
        if self.statut_verification == StatutVerification.VERIFIE:
            raise ValueError("La création ne peut pas marquer automatiquement un souvenir comme vérifié")
        return self


class SouvenirUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1)
    date_evenement: date | None = None
    provenance: ProvenanceSouvenir | None = None
    details_provenance: str | None = Field(default=None, max_length=500)
    statut_verification: StatutVerification | None = None
    source_validation: str | None = Field(default=None, max_length=500)
    indices: list[IndiceCreate] | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self):
        for field in ("description", "provenance", "statut_verification"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} ne peut pas être nul")
        if (
            self.statut_verification == StatutVerification.VERIFIE
            and not self.source_validation
        ):
            raise ValueError("Une source est requise pour un souvenir vérifié")
        return self


class ValidationSouvenir(BaseModel):
    source_validation: str = Field(min_length=1, max_length=500)


class SouvenirRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    description: str
    date_evenement: date | None
    provenance: ProvenanceSouvenir
    details_provenance: str | None
    statut_verification: StatutVerification
    source_validation: str | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    elements: list[ElementRead]
    indices: list[IndiceRead]


class SessionTestCreate(BaseModel):
    patient_id: str
    protocole: str = Field(default="protocole-experimental", min_length=1, max_length=200)
    type_test: str = Field(min_length=1, max_length=50)
    seed: int = 0
    parametres: dict[str, Any] = Field(default_factory=dict)


class SessionTestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    configuration_id: str
    test_type: str
    test_version: str
    seed: int
    statut: str
    essai_courant: int
    started_at: datetime
    ended_at: datetime | None


class EssaiCourantRead(BaseModel):
    session_id: str
    test_type: str
    version: str
    essai_index: int
    phase: str
    condition: str
    stimulus: dict[str, Any]


class SoumissionEssai(BaseModel):
    essai_index: int = Field(ge=0)
    reponse: Any
    temps_reponse_ms: int | None = Field(default=None, ge=0)


class EvaluationEssaiRead(BaseModel):
    session_id: str
    essai_index: int
    condition: str
    score: float | None
    correcte: bool | None
    mesures: dict[str, Any]
    temps_reponse_ms: int | None
    session_terminee: bool
    prochain_essai_index: int | None


class ResultatEssaiRead(BaseModel):
    essai_index: int
    condition: str
    stimulus: dict[str, Any] | None
    reponse: Any
    reponse_attendue: Any | None
    score: float | None
    correcte: bool | None
    mesures: dict[str, Any]
    temps_reponse_ms: int | None
    created_at: datetime


class ResultatsSessionRead(BaseModel):
    session_id: str
    patient_id: str
    protocole_id: str
    protocole: str
    type_test: str
    version: str
    seed: int
    parametres: dict[str, Any]
    statut: str
    started_at: datetime
    ended_at: datetime | None
    resultats: list[ResultatEssaiRead]


class PerformanceConditionRead(BaseModel):
    nombre_essais: int
    score_moyen: float


class PerformanceTacheRead(BaseModel):
    nombre_essais: int
    score_moyen: float
    conditions: dict[str, PerformanceConditionRead]


class ProfilCognitifRead(BaseModel):
    patient_id: str
    sessions_terminees: int
    performances: dict[str, PerformanceTacheRead]
    avertissement: str


class RecuperationCreate(BaseModel):
    souvenir_id: str


class RecuperationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    souvenir_id: str
    statut: str
    strategie: str
    types_prioritaires: list[str]
    justification_strategie: str
    assistance_externe_consultee: bool
    resultat_final: ResultatRecuperation | None
    started_at: datetime
    ended_at: datetime | None


class IndiceRecuperationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ordre: int
    indice_id: str | None
    indice_type: str
    indice_contenu: str
    niveau_aide: int
    raison_selection: str
    presented_at: datetime


class FeedbackRecuperationCreate(BaseModel):
    tentative_id: str
    feedback: FeedbackRecuperation
    reponse_patient: str | None = Field(default=None, max_length=2000)
    souvenir_evoque: str | None = Field(default=None, min_length=1, max_length=2000)


class FeedbackRecuperationRead(BaseModel):
    tentative_id: str
    feedback: FeedbackRecuperation
    candidat_id: str | None


class TerminaisonRecuperationCreate(BaseModel):
    resultat: ResultatRecuperation


class TentativeRecuperationRead(IndiceRecuperationRead):
    feedback: FeedbackRecuperation | None
    reponse_patient: str | None
    responded_at: datetime | None


class CandidatSouvenirRead(BaseModel):
    id: str
    description: str
    provenance: ProvenanceSouvenir
    statut: str
    created_at: datetime


class HistoriqueRecuperationRead(RecuperationRead):
    tentatives: list[TentativeRecuperationRead]
    candidats: list[CandidatSouvenirRead]


class ElementMemoireExterneRead(BaseModel):
    type: TypeElement
    contenu: str


class MemoireExterneRead(BaseModel):
    souvenir_id: str
    description: str
    date_evenement: date | None
    provenance: ProvenanceSouvenir
    details_provenance: str | None
    statut_verification: StatutVerification
    presentation_comme_fait_verifie: bool
    avertissement: str
    elements: list[ElementMemoireExterneRead]

