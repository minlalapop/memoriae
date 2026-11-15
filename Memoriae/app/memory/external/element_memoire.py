from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.memory.external.enums import TypeElement
from app.persistence.database import Base, new_id, utc_now

if TYPE_CHECKING:
    from app.memory.external.souvenir import Souvenir


class ElementMemoire(Base):
    __tablename__ = "elements_memoire"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    souvenir_id: Mapped[str] = mapped_column(
        ForeignKey("souvenirs.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[TypeElement] = mapped_column(Enum(TypeElement, native_enum=False))
    contenu: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    souvenir: Mapped[Souvenir] = relationship(back_populates="elements")
