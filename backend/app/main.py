from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .agent import HCPAgent
from .database import Base, engine, get_db
from .models import HCP, Interaction
from .schemas import AgentResponse, ChatRequest, HCPRead, InteractionCreate, InteractionRead, InteractionUpdate
from .settings import settings


Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_hcps(db: Session) -> None:
    if db.query(HCP).count():
        return
    db.add_all(
        [
            HCP(
                name="Dr. Aarav Mehta",
                specialty="Cardiologist",
                segment="A",
                affiliation="Apollo Heart Institute",
                preferred_channel="In-person",
            ),
            HCP(
                name="Dr. Nisha Rao",
                specialty="Dermatologist",
                segment="B",
                affiliation="City Skin Clinic",
                preferred_channel="WhatsApp",
            ),
            HCP(
                name="Dr. Kabir Shah",
                specialty="Oncologist",
                segment="A",
                affiliation="Metro Cancer Centre",
                preferred_channel="Email",
            ),
        ]
    )
    db.commit()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "llm_model": settings.groq_model}


@app.get("/api/hcps", response_model=list[HCPRead])
def list_hcps(db: Session = Depends(get_db)) -> list[HCP]:
    seed_hcps(db)
    return db.query(HCP).order_by(HCP.name).all()


@app.get("/api/interactions", response_model=list[InteractionRead])
def list_interactions(db: Session = Depends(get_db)) -> list[Interaction]:
    return db.query(Interaction).order_by(Interaction.created_at.desc()).limit(25).all()


@app.post("/api/interactions")
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)) -> dict:
    seed_hcps(db)
    if not db.get(HCP, payload.hcp_id):
        raise HTTPException(status_code=404, detail="HCP not found")
    return HCPAgent(db).log_interaction(payload)


@app.patch("/api/interactions/{interaction_id}")
def update_interaction(
    interaction_id: int,
    payload: InteractionUpdate,
    db: Session = Depends(get_db),
) -> dict:
    result = HCPAgent(db).edit_interaction(interaction_id, payload)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/agent/chat", response_model=AgentResponse)
def agent_chat(payload: ChatRequest, db: Session = Depends(get_db)) -> AgentResponse:
    seed_hcps(db)
    result = HCPAgent(db).invoke(payload.message, payload.hcp_id)
    return AgentResponse(
        intent=result["intent"],
        answer=result["answer"],
        tool_output=result["tool_output"],
    )


@app.get("/api/agent/tools/demo")
def tools_demo(db: Session = Depends(get_db)) -> dict:
    seed_hcps(db)
    return HCPAgent(db).run_all_tools_demo()
