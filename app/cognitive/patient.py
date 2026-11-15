from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.database import Base, new_id, utc_now

if TYPE_CHECKING:
    from app.memory.external.souvenir import Souvenir
    from app.persistence.models import CandidatSouvenir, SessionRecuperation, SessionTest


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (CheckConstraint("age IS NULL OR age BETWEEN 0 AND 130"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    nom: Mapped[str] = mapped_column(String(200))
    prenom: Mapped[str | None] = mapped_column(String(200), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    est_fictif: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consentement: Mapped[bool] = mapped_column(Boolean, default=False)
    date_consentement: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    souvenirs: Mapped[list[Souvenir]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[SessionTest]] = relationship(back_populates="patient")
    sessions_recuperation: Mapped[list[SessionRecuperation]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    candidats_souvenir: Mapped[list[CandidatSouvenir]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
