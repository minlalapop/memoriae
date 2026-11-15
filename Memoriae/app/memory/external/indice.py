from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.database import Base, new_id, utc_now

if TYPE_CHECKING:
    from app.memory.external.souvenir import Souvenir


class Indice(Base):
    __tablename__ = "indices"
    __table_args__ = (
        CheckConstraint("score_pertinence IS NULL OR score_pertinence BETWEEN 0 AND 1"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    souvenir_id: Mapped[str] = mapped_column(
        ForeignKey("souvenirs.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(100))
    contenu: Mapped[str] = mapped_column(Text)
    score_pertinence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    souvenir: Mapped[Souvenir] = relationship(back_populates="indices")
