from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import create_item, list_items
from app.database import Base, engine, get_db
from app.models import Item
from app.schemas import ItemCreate, ItemRead

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.app_name}


@app.post("/chat")
def chat(payload: dict):
    message = str(payload.get("message", ""))
    return {
        "message": message,
        "pii_detected": {},
        "pii_metadata": {},
        "response": "This is the Betty starter backend. Add the AI monitor backend for full prompt-tracking features.",
        "model": str(payload.get("model", "mock-model")),
        "event_id": None,
    }


@app.post("/agent/run")
def run_agent(payload: dict):
    agent_id = str(payload.get("agent_id", "starter-agent"))
    started_at = datetime.now(timezone.utc).isoformat()
    return {
        "agent_id": agent_id,
        "declared": [],
        "observed": [],
        "unexpected": [],
        "unused_declared": [],
        "status": "completed",
        "tools_invoked": [],
        "tool_calls": [],
        "run_id": "starter-run",
        "started_at": started_at,
        "finished_at": started_at,
        "governance_alert": False,
        "governance_alert_reason": "",
    }


@app.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total = db.query(Item).count()
    return {"total_events": total, "applications": ["items", "chat", "agent"]}


@app.get("/dashboard/usage")
def dashboard_usage(db: Session = Depends(get_db)):
    items = db.query(Item).order_by(Item.id.desc()).limit(10).all()
    return [{
        "id": item.id,
        "application": "items",
        "event_type": "item_access",
        "created_at": item.created_at.isoformat() if item.created_at else None,
    } for item in items]


@app.get("/dashboard/prompts")
def list_prompts():
    return []


@app.get("/dashboard/prompts/pii-summary")
def pii_summary_by_asset():
    return {}


@app.get("/dashboard/runs")
def list_runs(limit: int = 50):
    return []


@app.get("/dashboard/runs/{run_id}")
def get_run(run_id: str):
    return {"run_id": run_id, "status": "completed", "tool_calls": [], "unexpected": []}


@app.get("/items", response_model=list[ItemRead])
def read_items(db: Session = Depends(get_db)):
    return list_items(db)


@app.post("/items", response_model=ItemRead)
def create_new_item(item: ItemCreate, db: Session = Depends(get_db)):
    return create_item(db, item)
