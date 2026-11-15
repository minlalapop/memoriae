from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.memory.external.enums import ProvenanceSouvenir, StatutVerification
from app.persistence.database import Base, new_id, utc_now

if TYPE_CHECKING:
    from app.cognitive.patient import Patient
    from app.memory.external.element_memoire import ElementMemoire
    from app.memory.external.indice import Indice
    from app.persistence.models import SessionRecuperation


class Souvenir(Base):
    __tablename__ = "souvenirs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text)
    date_evenement: Mapped[date | None] = mapped_column(Date)
    provenance: Mapped[ProvenanceSouvenir] = mapped_column(
        Enum(ProvenanceSouvenir, native_enum=False)
    )
    details_provenance: Mapped[str | None] = mapped_column(String(500))
    statut_verification: Mapped[StatutVerification] = mapped_column(
        Enum(StatutVerification, native_enum=False), default=StatutVerification.NON_VERIFIE
    )
    source_validation: Mapped[str | None] = mapped_column(String(500))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    patient: Mapped[Patient] = relationship(back_populates="souvenirs")
    elements: Mapped[list[ElementMemoire]] = relationship(
        back_populates="souvenir",
        cascade="all, delete-orphan",
        order_by="ElementMemoire.created_at",
    )
    indices: Mapped[list[Indice]] = relationship(
        back_populates="souvenir",
        cascade="all, delete-orphan",
        order_by="Indice.created_at",
    )
    sessions_recuperation: Mapped[list[SessionRecuperation]] = relationship(
        back_populates="souvenir", cascade="all, delete-orphan"
    )
