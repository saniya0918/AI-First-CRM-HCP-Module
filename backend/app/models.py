from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class HCP(Base):
    __tablename__ = "hcps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    segment: Mapped[str] = mapped_column(String(40), default="B")
    affiliation: Mapped[str] = mapped_column(String(160), default="")
    preferred_channel: Mapped[str] = mapped_column(String(40), default="In-person")

    interactions: Mapped[list["Interaction"]] = relationship(back_populates="hcp")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(60), default="Detailing")
    products_discussed: Mapped[str] = mapped_column(String(240), default="")
    sentiment: Mapped[str] = mapped_column(String(40), default="Neutral")
    outcome: Mapped[str] = mapped_column(String(160), default="")
    next_step: Mapped[str] = mapped_column(String(240), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    extracted_entities: Mapped[str] = mapped_column(Text, default="{}")
    compliance_status: Mapped[str] = mapped_column(String(40), default="Not checked")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp: Mapped[HCP] = relationship(back_populates="interactions")
