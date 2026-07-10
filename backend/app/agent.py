import json
import re
from datetime import date, timedelta
from typing import Any, TypedDict

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from .models import HCP, Interaction
from .schemas import InteractionCreate, InteractionUpdate
from .settings import settings


class AgentState(TypedDict, total=False):
    message: str
    hcp_id: int | None
    intent: str
    tool_output: dict[str, Any]
    answer: str


RISK_PHRASES = {
    "guaranteed": "Avoid guaranteed efficacy claims.",
    "off-label": "Potential off-label discussion needs medical review.",
    "cure": "Avoid cure claims unless approved labeling supports it.",
    "adverse event": "Possible adverse event mention requires escalation.",
    "side effect": "Possible adverse event mention requires escalation.",
    "discount": "Pricing claims may require market access approval.",
}


def _llm() -> ChatGroq | None:
    if not settings.groq_api_key:
        return None
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.2,
    )


def summarize_and_extract(notes: str, products: str = "") -> dict[str, Any]:
    model = _llm()
    if model:
        prompt = (
            "You are an AI assistant for a compliant life-sciences CRM. "
            "Summarize this HCP interaction in one sentence and extract entities. "
            "Return strict JSON with keys summary, products, objections, follow_up.\n\n"
            f"Products: {products}\nNotes: {notes}"
        )
        try:
            content = model.invoke(prompt).content
            match = re.search(r"\{.*\}", content, re.S)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass

    product_list = [item.strip() for item in products.split(",") if item.strip()]
    follow_up = "Schedule follow-up" if "follow" in notes.lower() else "Not specified"
    return {
        "summary": notes[:180] + ("..." if len(notes) > 180 else ""),
        "products": product_list,
        "objections": re.findall(r"(?:concern|objection|barrier)[: -]+([^.;]+)", notes, flags=re.I),
        "follow_up": follow_up,
    }


def extract_form_patch(message: str) -> dict[str, Any]:
    model = _llm()
    if model:
        prompt = (
            "Extract CRM form fields from this HCP interaction message. "
            "Return strict JSON only with any fields you can infer from: "
            "hcp_name, interaction_type, date, time, attendees, topics_discussed, "
            "materials_shared, samples_distributed, sentiment, outcomes, follow_up_actions, "
            "products_discussed. Use ISO date when possible. Message:\n"
            f"{message}"
        )
        try:
            content = model.invoke(prompt).content
            match = re.search(r"\{.*\}", content, re.S)
            if match:
                return {key: value for key, value in json.loads(match.group(0)).items() if value not in ("", None, [])}
        except Exception:
            pass

    patch: dict[str, Any] = {}
    name_match = re.search(r"\bDr\.?\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?", message)
    if name_match:
        patch["hcp_name"] = name_match.group(0).replace("Dr ", "Dr. ")

    lower_message = message.lower()
    if "today" in lower_message:
        patch["date"] = str(date.today())
    if "meeting" in lower_message or "met" in lower_message:
        patch["interaction_type"] = "Meeting"
    if "brochure" in lower_message:
        patch["materials_shared"] = "Brochures"
    if "sample" in lower_message:
        patch["samples_distributed"] = "Samples distributed"
    if "positive" in lower_message:
        patch["sentiment"] = "Positive"
    elif "negative" in lower_message:
        patch["sentiment"] = "Negative"
    elif "neutral" in lower_message:
        patch["sentiment"] = "Neutral"

    product_match = re.search(r"product\s+([A-Za-z0-9 -]+)", message, flags=re.I)
    if product_match:
        patch["products_discussed"] = product_match.group(1).strip(" .")

    patch["topics_discussed"] = message
    if "follow" in lower_message:
        patch["follow_up_actions"] = "Schedule follow-up"
    if "agreed" in lower_message or "requested" in lower_message:
        patch["outcomes"] = message
    return patch


@tool
def log_interaction_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """Capture HCP interaction data with AI summary and entity extraction."""
    return {"tool": "log_interaction", "received": payload}


@tool
def edit_interaction_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """Modify an existing logged interaction and refresh AI-enriched fields."""
    return {"tool": "edit_interaction", "received": payload}


@tool
def fetch_hcp_profile_tool(hcp_id: int) -> dict[str, Any]:
    """Fetch HCP profile context for the representative."""
    return {"tool": "fetch_hcp_profile", "hcp_id": hcp_id}


@tool
def suggest_next_action_tool(context: dict[str, Any]) -> dict[str, Any]:
    """Recommend the next best sales action based on HCP context."""
    return {"tool": "suggest_next_action", "context": context}


@tool
def compliance_check_tool(notes: str) -> dict[str, Any]:
    """Check notes for compliance-sensitive language."""
    return {"tool": "compliance_check", "notes": notes}


@tool
def schedule_follow_up_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a follow-up recommendation for the HCP."""
    return {"tool": "schedule_follow_up", "received": payload}


class HCPAgent:
    def __init__(self, db: Session):
        self.db = db
        graph = StateGraph(AgentState)
        graph.add_node("classify", self._classify)
        graph.add_node("run_tool", self._run_tool)
        graph.add_edge(START, "classify")
        graph.add_edge("classify", "run_tool")
        graph.add_edge("run_tool", END)
        self.graph = graph.compile()

    def invoke(self, message: str, hcp_id: int | None = None) -> AgentState:
        return self.graph.invoke({"message": message, "hcp_id": hcp_id})

    def _classify(self, state: AgentState) -> AgentState:
        message = state["message"].lower()
        if "edit" in message or "update" in message or "change" in message:
            intent = "edit_interaction"
        elif "profile" in message or "who is" in message:
            intent = "fetch_hcp_profile"
        elif "next" in message or "recommend" in message:
            intent = "suggest_next_action"
        elif "compliance" in message or "check" in message:
            intent = "compliance_check"
        elif "follow" in message or "schedule" in message:
            intent = "schedule_follow_up"
        else:
            intent = "log_interaction"
        return {**state, "intent": intent}

    def _run_tool(self, state: AgentState) -> AgentState:
        intent = state["intent"]
        if intent == "edit_interaction":
            output = self.edit_interaction_from_message(state["message"])
        elif intent == "fetch_hcp_profile":
            output = self.fetch_hcp_profile(state.get("hcp_id") or 1)
        elif intent == "suggest_next_action":
            output = self.suggest_next_action(state.get("hcp_id") or 1, state["message"])
        elif intent == "compliance_check":
            output = self.compliance_check(state["message"])
        elif intent == "schedule_follow_up":
            output = self.schedule_follow_up(state.get("hcp_id") or 1, "Discuss product access and patient fit")
        else:
            hcp_id = state.get("hcp_id") or 1
            output = self.log_interaction(
                InteractionCreate(
                    hcp_id=hcp_id,
                    channel="Chat",
                    interaction_type="AI-assisted note",
                    products_discussed=self._extract_products(state["message"]),
                    sentiment=self._extract_sentiment(state["message"]),
                    outcome="Captured from conversational note",
                    next_step="AI to recommend next action",
                    notes=state["message"],
                )
            )

        return {
            **state,
            "tool_output": output,
            "answer": f"{intent.replace('_', ' ').title()} completed.",
        }

    def log_interaction(self, payload: InteractionCreate) -> dict[str, Any]:
        form_patch = extract_form_patch(payload.notes)
        enrichment = summarize_and_extract(payload.notes, payload.products_discussed)
        compliance = self.compliance_check(payload.notes)
        interaction = Interaction(
            hcp_id=payload.hcp_id,
            channel=payload.channel,
            interaction_type=payload.interaction_type,
            products_discussed=payload.products_discussed,
            sentiment=payload.sentiment,
            outcome=payload.outcome,
            next_step=payload.next_step,
            notes=payload.notes,
            ai_summary=enrichment["summary"],
            extracted_entities=json.dumps(enrichment),
            compliance_status=compliance["status"],
        )
        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)
        return {
            "tool": "log_interaction",
            "interaction_id": interaction.id,
            "form_patch": {
                **form_patch,
                "topics_discussed": form_patch.get("topics_discussed", payload.notes),
                "products_discussed": payload.products_discussed or form_patch.get("products_discussed", ""),
                "sentiment": payload.sentiment or form_patch.get("sentiment", "Neutral"),
                "outcomes": payload.outcome,
                "follow_up_actions": payload.next_step,
            },
            "summary": interaction.ai_summary,
            "entities": enrichment,
            "compliance": compliance,
        }

    def edit_interaction_from_message(self, message: str) -> dict[str, Any]:
        patch = extract_form_patch(message)
        return {
            "tool": "edit_interaction",
            "form_patch": patch,
            "updated_fields": list(patch.keys()),
            "instruction": "Apply only these fields to the current draft form.",
        }

    def edit_interaction(self, interaction_id: int, payload: InteractionUpdate) -> dict[str, Any]:
        interaction = self.db.get(Interaction, interaction_id)
        if not interaction:
            return {"tool": "edit_interaction", "error": f"Interaction {interaction_id} not found"}

        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(interaction, key, value)

        enrichment = summarize_and_extract(interaction.notes, interaction.products_discussed)
        interaction.ai_summary = enrichment["summary"]
        interaction.extracted_entities = json.dumps(enrichment)
        interaction.compliance_status = self.compliance_check(interaction.notes)["status"]
        self.db.commit()
        self.db.refresh(interaction)
        return {
            "tool": "edit_interaction",
            "interaction_id": interaction.id,
            "updated_fields": list(updates.keys()),
            "summary": interaction.ai_summary,
        }

    def fetch_hcp_profile(self, hcp_id: int) -> dict[str, Any]:
        hcp = self.db.get(HCP, hcp_id)
        if not hcp:
            return {"tool": "fetch_hcp_profile", "error": f"HCP {hcp_id} not found"}
        return {
            "tool": "fetch_hcp_profile",
            "hcp": {
                "id": hcp.id,
                "name": hcp.name,
                "specialty": hcp.specialty,
                "segment": hcp.segment,
                "affiliation": hcp.affiliation,
                "preferred_channel": hcp.preferred_channel,
            },
        }

    def suggest_next_action(self, hcp_id: int, context: str) -> dict[str, Any]:
        hcp = self.db.get(HCP, hcp_id)
        channel = hcp.preferred_channel if hcp else "Email"
        action = "Share approved clinical reprint and schedule a 15-minute follow-up"
        if "access" in context.lower():
            action = "Coordinate market access support and follow up on formulary questions"
        if "positive" in context.lower():
            action = "Invite HCP to peer education program and confirm patient profile fit"
        return {
            "tool": "suggest_next_action",
            "hcp_id": hcp_id,
            "recommendation": action,
            "channel": channel,
            "rationale": "Based on specialty context, sentiment, and stated next step.",
        }

    def compliance_check(self, notes: str) -> dict[str, Any]:
        lower_notes = notes.lower()
        findings = [
            {"phrase": phrase, "guidance": guidance}
            for phrase, guidance in RISK_PHRASES.items()
            if phrase in lower_notes
        ]
        return {
            "tool": "compliance_check",
            "status": "Needs review" if findings else "Compliant draft",
            "findings": findings,
        }

    def schedule_follow_up(self, hcp_id: int, topic: str) -> dict[str, Any]:
        return {
            "tool": "schedule_follow_up",
            "hcp_id": hcp_id,
            "date": str(date.today() + timedelta(days=7)),
            "channel": "Email",
            "topic": topic,
            "priority": "High" if "access" in topic.lower() else "Medium",
        }

    def run_all_tools_demo(self) -> dict[str, Any]:
        logged = self.log_interaction(
            InteractionCreate(
                hcp_id=1,
                channel="In-person",
                interaction_type="Detailing",
                products_discussed="CardioPlus",
                sentiment="Positive",
                outcome="HCP interested in patient selection data",
                next_step="Send approved reprint",
                notes="Dr. Mehta was positive about CardioPlus and asked for follow-up on access pathways.",
            )
        )
        interaction_id = logged["interaction_id"]
        return {
            "log_interaction": logged,
            "edit_interaction": self.edit_interaction(
                interaction_id,
                InteractionUpdate(next_step="Email approved reprint and schedule access discussion"),
            ),
            "fetch_hcp_profile": self.fetch_hcp_profile(1),
            "suggest_next_action": self.suggest_next_action(1, "positive access discussion"),
            "compliance_check": self.compliance_check("Discussed approved indication only. No off-label claims."),
            "schedule_follow_up": self.schedule_follow_up(1, "Review access pathways for CardioPlus"),
        }

    @staticmethod
    def _extract_products(message: str) -> str:
        known = ["CardioPlus", "DermaRelief", "OncoTrack", "Respira"]
        found = [product for product in known if product.lower() in message.lower()]
        return ", ".join(found)

    @staticmethod
    def _extract_sentiment(message: str) -> str:
        lower_message = message.lower()
        if any(word in lower_message for word in ["positive", "interested", "agreed"]):
            return "Positive"
        if any(word in lower_message for word in ["concern", "barrier", "objection"]):
            return "Concerned"
        return "Neutral"
