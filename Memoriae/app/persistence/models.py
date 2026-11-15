from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.cognitive.patient import Patient
from app.memory.external.enums import (
    FeedbackRecuperation,
    ProvenanceSouvenir,
    ResultatRecuperation,
    StatutVerification,
)
from app.memory.external.souvenir import Souvenir
from app.persistence.database import Base, new_id, utc_now


class ConfigurationExperience(Base):
    """Configuration versionnée conservée pour la reproductibilité."""

    __tablename__ = "configurations_experience"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    nom: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(50))
    parametres: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    sessions: Mapped[list[SessionTest]] = relationship(back_populates="configuration")


class SessionTest(Base):
    """Session expérimentale et copie figée de ses essais générés."""

    __tablename__ = "sessions_test"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    configuration_id: Mapped[str] = mapped_column(
        ForeignKey("configurations_experience.id")
    )
    test_type: Mapped[str] = mapped_column(String(50), default="non_specifie")
    test_version: Mapped[str] = mapped_column(String(20), default="0")
    seed: Mapped[int] = mapped_column(Integer, default=0)
    statut: Mapped[str] = mapped_column(String(20), default="en_cours")
    essai_courant: Mapped[int] = mapped_column(Integer, default=0)
    essais: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped[Patient] = relationship(back_populates="sessions")
    configuration: Mapped[ConfigurationExperience] = relationship(back_populates="sessions")
    reponses: Mapped[list[ReponseSession]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ReponseSession.essai_index",
    )


class ReponseSession(Base):
    __tablename__ = "reponses_session"
    __table_args__ = (
        CheckConstraint("temps_reponse_ms IS NULL OR temps_reponse_ms >= 0"),
        UniqueConstraint("session_id", "essai_index", name="uq_reponse_session_essai"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions_test.id", ondelete="CASCADE"), index=True
    )
    essai_index: Mapped[int | None] = mapped_column(Integer)
    condition: Mapped[str | None] = mapped_column(String(50))
    stimulus_ref: Mapped[str | None] = mapped_column(String(200))
    stimulus: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    contenu: Mapped[str] = mapped_column(Text)
    reponse_attendue: Mapped[Any | None] = mapped_column(JSON)
    score: Mapped[float | None] = mapped_column(Float)
    correcte: Mapped[bool | None] = mapped_column(Boolean)
    mesures: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    temps_reponse_ms: Mapped[int | None] = mapped_column(Integer)
    statut_verification: Mapped[StatutVerification] = mapped_column(
        Enum(StatutVerification, native_enum=False),
        default=StatutVerification.NON_VERIFIE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionTest] = relationship(back_populates="reponses")


class SessionRecuperation(Base):
    __tablename__ = "sessions_recuperation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    souvenir_id: Mapped[str] = mapped_column(
        ForeignKey("souvenirs.id", ondelete="CASCADE"), index=True
    )
    statut: Mapped[str] = mapped_column(String(20), default="en_cours")
    strategie: Mapped[str] = mapped_column(String(50))
    types_prioritaires: Mapped[list[str]] = mapped_column(JSON, default=list)
    justification_strategie: Mapped[str] = mapped_column(Text)
    assistance_externe_consultee: Mapped[bool] = mapped_column(Boolean, default=False)
    resultat_final: Mapped[ResultatRecuperation | None] = mapped_column(
        Enum(ResultatRecuperation, native_enum=False)
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped[Patient] = relationship(back_populates="sessions_recuperation")
    souvenir: Mapped[Souvenir] = relationship(back_populates="sessions_recuperation")
    tentatives: Mapped[list[TentativeRecuperation]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TentativeRecuperation.ordre",
    )
    candidats: Mapped[list[CandidatSouvenir]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class TentativeRecuperation(Base):
    __tablename__ = "tentatives_recuperation"
    __table_args__ = (
        UniqueConstraint("session_id", "ordre", name="uq_tentative_recuperation_ordre"),
        UniqueConstraint("session_id", "indice_id", name="uq_tentative_recuperation_indice"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions_recuperation.id", ondelete="CASCADE"), index=True
    )
    indice_id: Mapped[str | None] = mapped_column(
        ForeignKey("indices.id", ondelete="SET NULL"), index=True
    )
    ordre: Mapped[int] = mapped_column(Integer)
    indice_type: Mapped[str] = mapped_column(String(100))
    indice_contenu: Mapped[str] = mapped_column(Text)
    niveau_aide: Mapped[int] = mapped_column(Integer, default=0)
    raison_selection: Mapped[str] = mapped_column(Text)
    feedback: Mapped[FeedbackRecuperation | None] = mapped_column(
        Enum(FeedbackRecuperation, native_enum=False)
    )
    reponse_patient: Mapped[str | None] = mapped_column(Text)
    presented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[SessionRecuperation] = relationship(back_populates="tentatives")


class CandidatSouvenir(Base):
    """Évocation séparée de la mémoire externe, en attente de vérification humaine."""

    __tablename__ = "candidats_souvenir"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions_recuperation.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text)
    provenance: Mapped[ProvenanceSouvenir] = mapped_column(
        Enum(ProvenanceSouvenir, native_enum=False), default=ProvenanceSouvenir.PATIENT
    )
    statut: Mapped[str] = mapped_column(String(40), default="en_attente_verification")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    patient: Mapped[Patient] = relationship(back_populates="candidats_souvenir")
    session: Mapped[SessionRecuperation] = relationship(back_populates="candidats")


class Experience(Base):
    """Configuration publiée permettant de rejoindre un protocole par code."""

    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    nom: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    test_type: Mapped[str] = mapped_column(String(50))
    protocol_version: Mapped[str] = mapped_column(String(20))
    parametres: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    seed_base: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    participations: Mapped[list[ParticipantAccess]] = relationship(
        "ParticipantAccess", cascade="all, delete-orphan"
    )
    etapes: Mapped[list[EtapeExperience]] = relationship(
        "EtapeExperience",
        back_populates="experience",
        cascade="all, delete-orphan",
        order_by="EtapeExperience.position",
    )


class EtapeExperience(Base):
    """Test configuré et ordonné dans une expérience."""

    __tablename__ = "etapes_experience"
    __table_args__ = (
        UniqueConstraint("experience_id", "position", name="uq_etape_experience_position"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experience_id: Mapped[str] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    test_type: Mapped[str] = mapped_column(String(50))
    protocol_version: Mapped[str] = mapped_column(String(20))
    parametres: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    seed_offset: Mapped[int] = mapped_column(Integer, default=0)

    experience: Mapped[Experience] = relationship(back_populates="etapes")


class ParticipantAccess(Base):
    """Accès pseudonyme et borné à une seule session expérimentale."""

    __tablename__ = "participant_access"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    patient_id: Mapped[str | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions_test.id", ondelete="CASCADE"), unique=True, index=True
    )
    pseudonyme: Mapped[str] = mapped_column(String(50))
    est_fictif: Mapped[bool] = mapped_column(Boolean, default=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    experiment: Mapped[Experience] = relationship("Experience", overlaps="participations")
    session_test: Mapped[SessionTest] = relationship("SessionTest")
    executions: Mapped[list[ExecutionEtape]] = relationship(
        "ExecutionEtape",
        back_populates="participation",
        cascade="all, delete-orphan",
        order_by="ExecutionEtape.position",
    )


class ExecutionEtape(Base):
    """Lien entre une participation et les sessions figées de ses étapes."""

    __tablename__ = "executions_etape"
    __table_args__ = (
        UniqueConstraint("participant_access_id", "position", name="uq_execution_position"),
        UniqueConstraint("session_id", name="uq_execution_session"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    participant_access_id: Mapped[str] = mapped_column(
        ForeignKey("participant_access.id", ondelete="CASCADE"), index=True
    )
    etape_id: Mapped[str | None] = mapped_column(
        ForeignKey("etapes_experience.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions_test.id", ondelete="CASCADE"), unique=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer)

    participation: Mapped[ParticipantAccess] = relationship(back_populates="executions")
    session_test: Mapped[SessionTest] = relationship("SessionTest")


class ResearcherSession(Base):
    """Session chercheur persistée côté serveur."""

    __tablename__ = "researcher_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExecutionModele(Base):
    """Exécution computationnelle distincte des participations humaines."""

    __tablename__ = "executions_modele"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    model_id: Mapped[str] = mapped_column(String(100), index=True)
    model_version: Mapped[str] = mapped_column(String(50))
    protocol_version: Mapped[str] = mapped_column(String(50))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    statut: Mapped[str] = mapped_column(String(30), default="terminee")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    experience: Mapped[Experience] = relationship("Experience")
    resultats: Mapped[list[ResultatModele]] = relationship(
        "ResultatModele", cascade="all, delete-orphan", order_by="ResultatModele.essai_index"
    )


class ResultatModele(Base):
    __tablename__ = "resultats_modele"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions_modele.id", ondelete="CASCADE"), index=True
    )
    essai_index: Mapped[int] = mapped_column(Integer)
    stimulus_id: Mapped[str] = mapped_column(String(100), index=True)
    predicted_stimulus_id: Mapped[str] = mapped_column(String(100))
    correcte: Mapped[bool] = mapped_column(Boolean)
    mse: Mapped[float] = mapped_column(Float)
    mesures: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    execution: Mapped[ExecutionModele] = relationship(back_populates="resultats")
