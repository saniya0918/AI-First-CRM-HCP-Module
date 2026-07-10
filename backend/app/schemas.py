from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HCPRead(BaseModel):
    id: int
    name: str
    specialty: str
    segment: str
    affiliation: str
    preferred_channel: str

    model_config = {"from_attributes": True}


class InteractionCreate(BaseModel):
    hcp_id: int
    channel: str = "In-person"
    interaction_type: str = "Detailing"
    products_discussed: str = ""
    sentiment: str = "Neutral"
    outcome: str = ""
    next_step: str = ""
    notes: str = Field(min_length=5)


class InteractionUpdate(BaseModel):
    channel: str | None = None
    interaction_type: str | None = None
    products_discussed: str | None = None
    sentiment: str | None = None
    outcome: str | None = None
    next_step: str | None = None
    notes: str | None = None


class InteractionRead(BaseModel):
    id: int
    hcp_id: int
    channel: str
    interaction_type: str
    products_discussed: str
    sentiment: str
    outcome: str
    next_step: str
    notes: str
    ai_summary: str
    extracted_entities: str
    compliance_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(min_length=3)
    hcp_id: int | None = None


class AgentResponse(BaseModel):
    intent: str
    answer: str
    tool_output: dict[str, Any]
